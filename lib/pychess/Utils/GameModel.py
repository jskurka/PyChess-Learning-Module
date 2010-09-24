
from threading import RLock
import traceback
import cStringIO
import datetime

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

from pychess.Savers.ChessFile import LoadingError
from pychess.Players.Player import PlayerIsDead, TurnInterrupt
from pychess.System.ThreadPool import PooledThread
from pychess.System.protoopen import protoopen, protosave, isWriteable
from pychess.System.Log import log
from pychess.System import glock
from pychess.Variants.normal import NormalChess

from logic import getStatus, isClaimableDraw, playerHasMatingMaterial
from const import *

class GameModel (GObject, PooledThread):
    
    """ GameModel contains all available data on a chessgame.
        It also has the task of controlling players actions and moves """
    
    __gsignals__ = {
        "game_started":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_changed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "moves_undoing": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "game_unended":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_loading":  (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "game_loaded":   (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "game_saved":    (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        "game_ended":    (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "game_terminated":    (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_resumed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "action_error":  (SIGNAL_RUN_FIRST, TYPE_NONE, (object, int))
    }
    
    def __init__ (self, timemodel=None, variant=NormalChess):
        GObject.__init__(self)

        self.variant = variant
        self.boards = [variant.board(setup=True)]
        
        self.moves = []
        self.players = []
        
        self.status = WAITING_TO_START
        self.reason = UNKNOWN_REASON
        
        self.timemodel = timemodel
        
        today = datetime.date.today()
        self.tags = {
            "Event": _("Local Event"),
            "Site":  _("Local Site"),
            "Round": 1,
            "Year":  today.year,
            "Month": today.month,
            "Day":   today.day
        }
        
        # Keeps track of offers, so that accepts can be spotted
        self.offers = {}
        # True if the game has been changed since last save
        self.needsSave = False
        # The uri the current game was loaded from, or None if not a loaded game
        self.uri = None
        
        self.hintEngineSupportsVariant = False
        self.spyEngineSupportsVariant = False
        
        self.spectactors = {}
        
        self.applyingMoveLock = RLock()
    
    def setPlayers (self, players):
        assert self.status == WAITING_TO_START
        self.players = players
        for player in self.players:
            player.connect("offer", self.offerRecieved)
            player.connect("withdraw", self.withdrawRecieved)
            player.connect("decline", self.declineRecieved)
            player.connect("accept", self.acceptRecieved)
    
    def setSpectactors (self, spectactors):
        assert self.status == WAITING_TO_START
        self.spectactors = spectactors
    
    ############################################################################
    # Board stuff                                                              #
    ############################################################################
    
    def _get_ply (self):
        return self.boards[-1].ply
    ply = property(_get_ply)
    
    def _get_lowest_ply (self):
        return self.boards[0].ply
    lowply = property(_get_lowest_ply)
    
    def _get_curplayer (self):
        try:
            return self.players[self.getBoardAtPly(self.ply).color]
        except IndexError:
            log.error("%s %s\n" % (self.players, self.getBoardAtPly(self.ply).color))
            raise
    curplayer = property(_get_curplayer)
    
    def _plyToIndex (self, ply):
        index = ply - self.lowply
        if index < 0:
            raise IndexError, "%s < %s\n" % (ply, self.lowply)
        return index
    
    def getBoardAtPly (self, ply):
        try:
            return self.boards[self._plyToIndex(ply)]
        except:
            log.error("%d\t%d\t%d\t%d\n" % (self.lowply, ply, self.ply, len(self.boards)))
            raise
    
    def getMoveAtPly (self, ply):
        try:
            return self.moves[self._plyToIndex(ply)]
        except IndexError:
            log.error("%d\t%d\t%d\t%d\n" % (self.lowply, ply, self.ply, len(self.moves)))
            raise
    
    ############################################################################
    # Offer management                                                         #
    ############################################################################
    
    def offerRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if self.status not in UNFINISHED_STATES and offer.type in INGAME_ACTIONS:
            player.offerError(offer, ACTION_ERROR_REQUIRES_UNFINISHED_GAME)
        
        elif offer.type == RESUME_OFFER and self.status in (DRAW, WHITEWON,BLACKWON) and \
           self.reason in UNRESUMEABLE_REASONS:
            player.offerError(offer, ACTION_ERROR_UNRESUMEABLE_POSITION)
        
        elif offer.type == RESUME_OFFER and self.status != PAUSED:
            player.offerError(offer, ACTION_ERROR_RESUME_REQUIRES_PAUSED)
        
        elif offer.type == HURRY_ACTION:
            opPlayer.hurry()
        
        elif offer.type == CHAT_ACTION:
            opPlayer.putMessage(offer.param)
        
        elif offer.type == RESIGNATION:
            if player == self.players[WHITE]:
                self.end(BLACKWON, WON_RESIGN)
            else: self.end(WHITEWON, WON_RESIGN)
        
        elif offer.type == FLAG_CALL:
            if not self.timemodel:
                player.offerError(offer, ACTION_ERROR_NO_CLOCK)
                return
            
            if player == self.players[WHITE]:
                opcolor = BLACK
            else: opcolor = WHITE
            
            if self.timemodel.getPlayerTime (opcolor) <= 0:
                if self.timemodel.getPlayerTime (1-opcolor) <= 0:
                    self.end(DRAW, DRAW_CALLFLAG)
                elif not playerHasMatingMaterial(self.boards[-1], (1-opcolor)):
                    if opcolor == WHITE:
                        self.end(DRAW, DRAW_BLACKINSUFFICIENTANDWHITETIME)
                    else:
                        self.end(DRAW, DRAW_WHITEINSUFFICIENTANDBLACKTIME)
                else:
                    if player == self.players[WHITE]:
                        self.end(WHITEWON, WON_CALLFLAG)
                    else:
                        self.end(BLACKWON, WON_CALLFLAG)
            else:
                player.offerError(offer, ACTION_ERROR_NOT_OUT_OF_TIME)
        
        elif offer.type == DRAW_OFFER and isClaimableDraw(self.boards[-1]):
            reason = getStatus(self.boards[-1])[1]
            self.end(DRAW, reason)
        
        elif offer.type == TAKEBACK_OFFER and offer.param < self.lowply:
            player.offerError(offer, ACTION_ERROR_TOO_LARGE_UNDO)
        
        elif offer.type == TAKEBACK_OFFER and self.status != RUNNING and (
                                                   self.status not in UNDOABLE_STATES or
                                                   self.reason not in UNDOABLE_REASONS):
            player.offerError(offer, ACTION_ERROR_GAME_ENDED)
        
        elif offer.type in OFFERS:
            if offer not in self.offers:
                self.offers[offer] = player
                opPlayer.offer(offer)
            # If we updated an older offer, we want to delete the old one
            for offer_ in self.offers.keys():
                if offer.type == offer_.type and offer != offer_:
                    del self.offers[offer_]
    
    def withdrawRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offers and self.offers[offer] == player:
            del self.offers[offer]
            opPlayer.offerWithdrawn(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_WITHDRAW)
    
    def declineRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offers and self.offers[offer] == opPlayer:
            del self.offers[offer]
            opPlayer.offerDeclined(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_DECLINE)
    
    def acceptRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offers and self.offers[offer] == opPlayer:
            if offer.type == DRAW_OFFER:
                self.end(DRAW, DRAW_AGREE)
            elif offer.type == TAKEBACK_OFFER:
                self.undoMoves(self.ply - offer.param)
            elif offer.type == ADJOURN_OFFER:
                self.end(ADJOURNED, ADJOURNED_AGREEMENT)
            elif offer.type == ABORT_OFFER:
                self.end(ABORTED, ABORTED_AGREEMENT)
            elif offer.type == PAUSE_OFFER:
                self.pause()
            elif offer.type == RESUME_OFFER:
                self.resume()
            del self.offers[offer]
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)
    
    ############################################################################
    # Data stuff                                                               #
    ############################################################################
    
    def loadAndStart (self, uri, loader, gameno, position):
        assert self.status == WAITING_TO_START

        uriIsFile = type(uri) != str
        from pychess.Main import chessFiles
        if chessFiles.has_key(uri):
            chessfile = chessFiles[uri]
        else:
            if not uriIsFile:
                chessfile = loader.load(protoopen(uri))
            else: 
                chessfile = loader.load(uri)
        
        self.emit("game_loading", uri)
        try:
            chessfile.loadToModel(gameno, position, self)
        #Postpone error raising to make games loadable to the point of the error
        except LoadingError, e:
            error = e
        else: error = None
        self.emit("game_loaded", uri)
        
        self.needsSave = False
        if not uriIsFile:
            self.uri = uri
        else: self.uri = None
        
        if self.status == RUNNING:
            for player in self.players:
                player.setOptionInitialBoard(self)
            for spectactor in self.spectactors.values():
                spectactor.setOptionInitialBoard(self)
            
            if self.timemodel:
                self.timemodel.setMovingColor(self.boards[-1].color)
                if self.ply >= 2:
                    self.timemodel.start()
            
            self.status = WAITING_TO_START
            self.start()
        else:
            self.emit("game_started")
        
        if self.status == WHITEWON:
            self.emit("game_ended", self.reason)
        
        elif self.status == BLACKWON:
            self.emit("game_ended", self.reason)
        
        elif self.status == DRAW:
            self.emit("game_ended", self.reason)
        
        if error:
            raise error
    
    def save (self, uri, saver, append):
        if type(uri) == str:
            fileobj = protosave(uri, append)
            self.uri = uri
        else:
            fileobj = uri
            self.uri = None
        saver.save(fileobj, self)
        self.emit("game_saved", uri)
        self.needsSave = False
        
    ############################################################################
    # Run stuff                                                                #
    ############################################################################
    
    def run (self):
        # Avoid racecondition when self.start is called while we are in self.end
        if self.status != WAITING_TO_START:
            return
        self.status = RUNNING
        
        for player in self.players + self.spectactors.values():
            player.start()
        
        self.emit("game_started")
        
        while self.status in (PAUSED, RUNNING, DRAW, WHITEWON, BLACKWON):
            curColor = self.boards[-1].color
            curPlayer = self.players[curColor]
            
            if self.timemodel:
                curPlayer.updateTime(self.timemodel.getPlayerTime(curColor),
                                     self.timemodel.getPlayerTime(1-curColor))
            
            try:
                if self.ply > self.lowply:
                    move = curPlayer.makeMove(self.boards[-1],
                                              self.moves[-1],
                                              self.boards[-2])
                else: move = curPlayer.makeMove(self.boards[-1], None, None)
            except PlayerIsDead, e:
                if self.status in (WAITING_TO_START, PAUSED, RUNNING):
                    stringio = cStringIO.StringIO()
                    traceback.print_exc(file=stringio)
                    error = stringio.getvalue()
                    log.error("A Player died:%s\n%s" % (e, error), curPlayer)
                    if curColor == WHITE:
                        self.kill(WHITE_ENGINE_DIED)
                    else: self.kill(BLACK_ENGINE_DIED)
                break
            except TurnInterrupt:
                continue
            
            self.applyingMoveLock.acquire()
            try:
                self.needsSave = True
                newBoard = self.boards[-1].move(move)
                self.boards.append(newBoard)
                self.moves.append(move)
                if self.timemodel:
                    self.timemodel.tap()
                if not self.checkStatus():
                    pass
            finally:
                self.applyingMoveLock.release()
            
            self.emit("game_changed")
            
            for spectactor in self.spectactors.values():
                spectactor.putMove(self.boards[-1], self.moves[-1], self.boards[-2])
    
    def checkStatus (self):
        status, reason = getStatus(self.boards[-1])
        
        if status != RUNNING and self.status in (WAITING_TO_START, PAUSED, RUNNING):
            self.end(status, reason)
            return False
        
        if status != self.status and self.status in UNDOABLE_STATES \
                and self.reason in UNDOABLE_REASONS:
            self.__resume()
            self.status = status
            self.reason = UNKNOWN_REASON
            self.emit("game_unended")
        
        return True
    
    def __pause (self):
        for player in self.players:
            player.pause()
        try:
            for spectactor in self.spectactors.values():
                spectactor.pause()
        except NotImplementedError:
            pass
        if self.timemodel:
            self.timemodel.pause()
    
    def pause (self):
        """ Players will raise NotImplementedError if they doesn't support
            pause. Spectactors will be ignored. """
        
        glock.release()
        self.applyingMoveLock.acquire()
        glock.acquire()
        try:
            self.__pause()
            self.status = PAUSED
        finally:
            glock.release()
            self.applyingMoveLock.release()
            glock.acquire()
    
    def __resume (self):
        for player in self.players:
            player.resume()
        try:
            for spectactor in self.spectactors.values():
                spectactor.resume()
        except NotImplementedError:
            pass
        if self.timemodel:
            self.timemodel.resume()
        self.emit("game_resumed")
    
    def resume (self):
        glock.release()
        self.applyingMoveLock.acquire()
        glock.acquire()
        try:
            self.__resume()
            self.status = RUNNING
        finally:
            glock.release()
            self.applyingMoveLock.release()
    
    def end (self, status, reason):
        if self.status not in UNFINISHED_STATES:
            log.warn("Can't end a game that's already ended: %s %s" % (status, reason))
            return
        if self.status not in (WAITING_TO_START, PAUSED, RUNNING):
            self.needsSave = True
        
        #log.debug("Ending a game with status %d for reason %d\n%s" % (status, reason,
        #    "".join(traceback.format_list(traceback.extract_stack())).strip()))
        log.debug("Ending a game with status %d for reason %d\n" % (status, reason))
        self.status = status
        self.reason = reason
        
        self.emit("game_ended", reason)
        
        self.__pause()
    
    def kill (self, reason):
        log.debug("Killing a game for reason %d\n%s" % (reason,
            "".join(traceback.format_list(traceback.extract_stack())).strip()))
        
        self.status = KILLED
        self.reason = reason
        
        for player in self.players:
            player.end(self.status, reason)
        
        for spectactor in self.spectactors.values():
            spectactor.end(self.status, reason)
        
        if self.timemodel:
            self.timemodel.end()
        
        self.emit("game_ended", reason)
    
    def terminate (self):
        
        if self.status != KILLED:
            #self.resume()
            for player in self.players:
                player.end(self.status, self.reason)
            
            for spectactor in self.spectactors.values():
                spectactor.end(self.status, self.reason)
            
            if self.timemodel:
                self.timemodel.end()
        
        self.emit("game_terminated")
    
    ############################################################################
    # Other stuff                                                              #
    ############################################################################
    
    def undoMoves (self, moves):
        """ Will push back one full move by calling the undo methods of players
            and spectactors. """
        
        assert self.ply > 0
        self.emit("moves_undoing", moves)
        
        self.applyingMoveLock.acquire()
        try:
            self.needsSave = True
            
            del self.boards[-moves:]
            del self.moves[-moves:]
            
            for player in list(self.players) + list(self.spectactors.values()):
                player.undoMoves(moves, self)
            
            if self.timemodel:
                self.timemodel.undoMoves(moves)
            
            self.checkStatus()
        finally:
            self.applyingMoveLock.release()
    
    def isChanged (self):
        if self.ply == 0:
            return False
        if self.needsSave:
            return True
        if not self.uri or not isWriteable (self.uri):
            return True
        return False
