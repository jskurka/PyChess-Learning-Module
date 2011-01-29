import re
import time
from threading import RLock
import Queue
import itertools

from pychess.Utils.Move import *
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.Utils.Offer import Offer
from pychess.Utils.logic import validate, getMoveKillingKing
from pychess.Utils.const import *
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.System.Log import log
from pychess.System.ThreadPool import pool
from pychess.Variants import variants
from pychess.Savers.pgn import movre as movere

from ProtocolEngine import ProtocolEngine
from Player import PlayerIsDead, TurnInterrupt

def isdigits (strings):
    for s in strings:
        s = s.replace(".","")
        if s.startswith("-"):
            if not s[1:].isdigit():
                return False
        else:
            if not s.isdigit():
                return False
    return True

d_plus_dot_expr = re.compile(r"\d+\.")

anare = re.compile("""
    ^                        # beginning of string
    \s*                      #
    \d+ [+\-\.]?             # The ply analyzed. Some engines end it with a dot, minus or plus
    \s+                      #
    (-?Mat\s*\d+ | [-\d\.]+) # Mat1 is used by gnuchess to specify mate in one.
                             #        otherwise we should support a signed float
    \s+                      #
    [\d\.]+                  # The time used in seconds
    \s+                      #
    [\d\.]+                  # The score found in centipawns
    \s+                      #
    (.+)                     # The Principal-Variation. With or without move numbers
    \s*                      #
    $                        # end of string
    """, re.VERBOSE)
                   
#anare = re.compile("\d+\.?\s+ (Mat\d+|[-\d\.]+) \s+ \d+\s+\d+\s+((?:%s\s*)+)" % mov)

whitespaces = re.compile(r"\s+")

def semisynced(f):
    """ All moveSynced methods will be queued up, and called in the right
        order after self.readyMoves is true """
    def newFunction(*args, **kw):
        self = args[0]
        self.funcQueue.put((f, args, kw))

        if self.readyMoves:
            self.boardLock.acquire()
            try:
                while True:
                    try:
                        func_, args_, kw_ = self.funcQueue.get_nowait()
                        func_(*args_, **kw_)
                    except TypeError, e:
                        print "TypeError: %s" % repr(args)
                        raise
                    except Queue.Empty:
                        break
            finally:
                self.boardLock.release()
    return newFunction

# There is no way in the CECP protocol to determine if an engine not answering
# the protover=2 handshake with done=1 is old or just very slow. Thus we
# need a timeout after which we conclude the engine is 'protover=1' and will
# never answer. 
# XBoard will only give 2 seconds, but as we are quite sure that
# the engines support the protocol, we can add more. We don't add
# infinite time though, just in case.
# The engine can get more time by sending done=0
TIME_OUT_FIRST = 10

# The amount of seconds to add for the second timeout
TIME_OUT_SECOND = 15

class CECPEngine (ProtocolEngine):
    
    def __init__ (self, subprocess, color, protover):
        ProtocolEngine.__init__(self, subprocess, color, protover)
        
        self.features = {
            "ping":      0,
            "setboard":  0,
            "playother": 0,
            "san":       0,
            "usermove":  0,
            "time":      1,
            "draw":      1,
            "sigint":    0,
            "sigterm":   1,
            "reuse":     1,
            "analyze":   0,
            "myname":    ', '.join(self.defname),
            "variants":  "",
            "colors":    1,
            "ics":       0,
            "name":      0,
            "pause":     0,
            "nps":       0,
            "debug":     0,
            "memory":    0,
            "smp":       0,
            "egt":       '',
        }
        
        self.board = None
        # if self.engineIsInNotPlaying == True, engine is in "force" mode,
        # i.e. not thinking or playing, but still verifying move legality
        self.engineIsInNotPlaying = False 
        self.movenext = False
        self.waitingForMove = False
        self.readyForMoveNowCommand = False
        self.timeHandicap = 1
        
        self.lastping = 0
        self.lastpong = 0
        self.timeout = None
        
        self.returnQueue = Queue.Queue()
        self.engine.connect("line", self.parseLines)
        self.engine.connect("died", lambda e: self.returnQueue.put("del"))
        
        self.funcQueue = Queue.Queue()
        self.optionQueue = []
        self.boardLock = RLock()
        self.undoQueue = []
        
        self.connect("readyForOptions", self.__onReadyForOptions_before)
        self.connect_after("readyForOptions", self.__onReadyForOptions)
        self.connect_after("readyForMoves", self.__onReadyForMoves)
    
    #===========================================================================
    #    Starting the game
    #===========================================================================
    
    def prestart (self):
        print >> self.engine, "xboard"
        if self.protover == 1:
            self.emit("readyForOptions")
        elif self.protover == 2:
            print >> self.engine, "protover 2"
            self.timeout = time.time() + TIME_OUT_FIRST
    
    def start (self):
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            pool.start(self.__startBlocking)
        else:
            self.__startBlocking()
    
    def __startBlocking (self):
        if self.protover == 1:
            self.emit("readyForMoves")
        if self.protover == 2:
            try:
                r = self.returnQueue.get(True, max(self.timeout-time.time(),0))
                if r == "not ready":
                    # The engine has sent done=0, and parseLine has added more
                    # time to self.timeout
                    r = self.returnQueue.get(True, max(self.timeout-time.time(),0))
            except Queue.Empty:
                log.warn("Got timeout error\n", self.defname)
                self.emit("readyForOptions")
                self.emit("readyForMoves")
            else:
                if r == 'del':
                    raise PlayerIsDead
                assert r == "ready"
    
    def __onReadyForOptions_before (self, self_):
        self.readyOptions = True
    
    def __onReadyForOptions (self, self_):
        # This is no longer needed
        #self.timeout = time.time()
        
        # Some engines has the 'post' option enabled by default, and posts a lot
        # of debug information. Generelly this only help to increase the log
        # file size, and we don't really need it.
        print >> self.engine, "nopost"
        
        for command in self.optionQueue:
            print >> self.engine, command
        
    def __onReadyForMoves (self, self_):
        # If we are an analyzer, this signal was already called in a different
        # thread, so we can safely block it.
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            if not self.board:
                self.board = Board(setup=True)
            self.__sendAnalyze(self.mode == INVERSE_ANALYZING)
        
        self.readyMoves = True
        semisynced(lambda s:None)(self)
    
    #===========================================================================
    #    Ending the game
    #===========================================================================
    
    @semisynced
    def end (self, status, reason):
        if self.connected:
            # We currently can't fillout the comment "field" as the repr strings
            # for reasons and statuses lies in Main.py
            # Creating Status and Reason class would solve this
            if status == DRAW:
                print >> self.engine, "result 1/2-1/2 {?}"
            elif status == WHITEWON:
                print >> self.engine, "result 1-0 {?}"
            elif status == BLACKWON:
                print >> self.engine, "result 0-1 {?}"
            else:
                print >> self.engine, "result * {?}"
            
            # Make sure the engine exits and do some cleaning
            self.kill(reason)
    
    def kill (self, reason):
        """ Kills the engine, starting with the 'quit' command, then sigterm and
            eventually sigkill.
            Returns the exitcode, or if engine have already been killed, returns
            None """
        if self.connected:
            self.connected = False
            try:
                try:
                    print >> self.engine, "quit"
                    self.returnQueue.put("del")
                    self.engine.gentleKill()
                
                except OSError, e:
                    # No need to raise on a hang up error, as the engine is dead
                    # anyways
                    if e.errno == 32:
                        log.warn("Hung up Error", self.defname)
                        return e.errno
                    else: raise
            
            finally:
                # Clear the analyzed data, if any
                self.emit("analyze", [], None)
    
    #===========================================================================
    #    Send the player move updates
    #===========================================================================
    
    @semisynced
    def putMove (self, board1, move, board2):
        """ Sends the engine the last move made (for spectator engines).
            @param board1: The current board
            @param move: The last move made
            @param board2: The board before the last move was made
        """
        self.board = board1
        
        if not board2:
            self.__tellEngineToPlayCurrentColorAndMakeMove()
            self.movenext = False
            return
        
        if self.mode == INVERSE_ANALYZING:
            self.board = self.board.switchColor()
            self.__printColor()
        
        self.__usermove(board2, move)
        
        if self.mode == INVERSE_ANALYZING:
            if self.board.board.opIsChecked():
                # Many engines don't like positions able to take down enemy
                # king. Therefore we just return the "kill king" move
                # automaticaly
                self.emit("analyze", [getMoveKillingKing(self.board)], MATE_VALUE-1)
                return
            self.__printColor()
    
    def makeMove (self, board1, move, board2):
        """ Gets a move from the engine (for player engines).
            @param board1: The current board
            @param move: The last move made
            @param board2: The board before the last move was made
            @return: The move the engine decided to make
        """
        log.debug("makeMove: move=%s self.movenext=%s board1=%s board2=%s self.board=%s\n" % \
            (move, self.movenext, board1, board2, self.board), self.defname)
        assert self.readyMoves
        
        self.boardLock.acquire()
        try:
            if self.board == board1 or not board2 or self.movenext:
                self.board = board1
                self.__tellEngineToPlayCurrentColorAndMakeMove()
                self.movenext = False
            else:
                self.board = board1
                self.__usermove(board2, move)
                
                if self.engineIsInNotPlaying:
                    self.__tellEngineToPlayCurrentColorAndMakeMove()
        finally:
            self.boardLock.release()
        self.waitingForMove = True
        self.readyForMoveNowCommand = True
        
        # Parse outputs
        r = self.returnQueue.get()
        if r == "not ready":
            log.warn("Engine seems to be protover=2, but is treated as protover=1", self.defname)
            r = self.returnQueue.get()
        if r == "ready":
            r = self.returnQueue.get()
        if r == "del":
            raise PlayerIsDead, "Killed by foreign forces"
        if r == "int":
            raise TurnInterrupt
        
        self.waitingForMove = False
        self.readyForMoveNowCommand = False
        assert isinstance(r, Move), r
        return r
    
    @semisynced
    def updateTime (self, secs, opsecs):
        print >> self.engine, "time", int(secs*100*self.timeHandicap)
        print >> self.engine, "otim", int(opsecs*100)
    
    #===========================================================================
    #    Standard options
    #===========================================================================
    
    def setOptionAnalyzing (self, mode):
        self.mode = mode
    
    def setOptionInitialBoard (self, model):
        # We don't use the optionQueue here, as set board prints a whole lot of
        # stuff. Instead we just call it, and let semisynced handle the rest.
        self.setBoard(model.boards[:], model.moves[:])
    
    @semisynced
    def setBoard (self, boards, moves):
        # Notice: If this method is to be called while playing, the engine will
        # need 'new' and an arrangement simmilar to that of 'pause' to avoid
        # the current thought move to appear
        
        self.boardLock.acquire()
        try:
            self.__tellEngineToStopPlayingCurrentColor()
            if boards[0].asFen() != FEN_START:
                self.__setBoard(boards[0])
            
            for board, move in zip(boards[:-1], moves):
                self.__usermove(board, move)
            
            if self.mode in (ANALYZING, INVERSE_ANALYZING):
                self.board = boards[-1]
            
            if self.mode == INVERSE_ANALYZING:
                self.board = self.board.switchColor()
                self.__printColor()
            
            #if self.mode in (ANALYZING, INVERSE_ANALYZING) or \
            #        gamemodel.boards[-1].color == self.color:
            #    self.board = gamemodel.boards[-1]
            #    if self.mode == ANALYZING:
            #        self.analyze()
            #    elif self.mode == INVERSE_ANALYZING:
            #        self.analyze(inverse=True)
            #    else:
            #        self.movenext = True
        finally:
            self.boardLock.release()
    
    def setOptionVariant (self, variant):
        if variant in variants.values() and not variant.standard_rules:
            assert variant.cecp_name in self.features["variants"], \
                    "%s dosn't support %s variant" % (self, variant.cecp_name)
            self.optionQueue.append("variant %s" % variant.cecp_name)
    
        #==================================================#
        #    Strength system                               #
        #==================================================#
        #          Strength  Depth  Ponder  Time handicap  #
        #    Easy  1         1      o       o              #
        #          2         2      o       o              #
        #          3         3      o       o              #
        #    Semi  4         5      o       10,00%         #
        #          5         7      o       20,00%         #
        #          6         9      o       40,00%         #
        #    Hard  7         o      x       80,00%         #
        #          8         o      x       o              #
        #==================================================#
    
    def setOptionStrength (self, strength):
        self.strength = strength
        
        if 4 <= strength <= 7:
            self.__setTimeHandicap(0.1 * 2**(strength-4))
        
        if strength <= 3:
            self.__setDepth(strength)
        elif strength <= 6:
            self.__setDepth(5+(strength-4)*2)
        
        self.__setPonder(strength >= 7)
        
        if strength == 8:
            self.optionQueue.append("egtb")
        else:
            self.optionQueue.append("random")
    
    def __setDepth (self, depth):
        self.optionQueue.append("sd %d" % depth)
    
    def __setTimeHandicap (self, timeHandicap):
        self.timeHandicap = timeHandicap
    
    def __setPonder (self, ponder):
        if ponder:
            self.optionQueue.append("hard")
        else:
            self.optionQueue.append("hard")
            self.optionQueue.append("easy")
    
    def setOptionTime (self, secs, gain):
        # Notice: In CECP we apply time handicap in updateTime, not in
        #         setOptionTime. 
        
        minutes = int(secs / 60)
        secs = int(secs % 60)
        s = str(minutes)
        if secs:
            s += ":" + str(secs)
        
        self.optionQueue.append("level 0 %s %d" % (s, gain))
    
    #===========================================================================
    #    Interacting with the player
    #===========================================================================
    
    @semisynced
    def pause (self):
        """ Pauses engine using the "pause" command if available. Otherwise put
            engine in force mode. By the specs the engine shouldn't ponder in
            force mode, but some of them do so anyways. """
        
        self.engine.pause()
        return
        
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            return
        if self.features["pause"]:
            print >> self.engine, "pause"
        elif self.board:
            self.__tellEngineToStopPlayingCurrentColor()
            self._blockTillMove()
    
    @semisynced
    def resume (self):
        self.engine.resume()
        return
        
        if self.mode not in (ANALYZING, INVERSE_ANALYZING):
            if self.features["pause"]:
                print "features resume"
                print >> self.engine, "resume"
            elif self.board:
                print "go resume"
                self.__tellEngineToPlayCurrentColorAndMakeMove()
    
    @semisynced
    def hurry (self):
        log.debug("hurry: self.waitingForMove=%s self.readyForMoveNowCommand=%s\n" % \
            (self.waitingForMove, self.readyForMoveNowCommand), self.defname)
        if self.waitingForMove and self.readyForMoveNowCommand:
            self.__tellEngineToMoveNow()
            self.readyForMoveNowCommand = False
    
    @semisynced
    def spectatorUndoMoves (self, moves, gamemodel):
        log.debug("spectatorUndoMoves: moves=%s gamemodel.ply=%s gamemodel.boards[-1]=%s self.board=%s\n" % \
            (moves, gamemodel.ply, gamemodel.boards[-1], self.board), self.defname)
        if self.mode == INVERSE_ANALYZING:
            self.board = self.board.switchColor()
            self.__printColor()
        
        for i in xrange(moves):
            print >> self.engine, "undo"
        
        self.board = gamemodel.boards[-1]
        
        if self.mode == INVERSE_ANALYZING:
            self.board = self.board.switchColor()
            self.__printColor()
    
    @semisynced
    def playerUndoMoves (self, moves, gamemodel):
        log.debug("playerUndoMoves: moves=%s gamemodel.ply=%s gamemodel.boards[-1]=%s self.board=%s\n" % \
            (moves, gamemodel.ply, gamemodel.boards[-1], self.board), self.defname)
        
        if gamemodel.curplayer != self and moves % 2 == 1:
            # Interrupt if we were searching, but should no longer do so
            self.returnQueue.put("int")
        
        self.__tellEngineToStopPlayingCurrentColor()
        if self.board and gamemodel.status in UNFINISHED_STATES:
            log.debug("playerUndoMoves: self.__tellEngineToMoveNow(), self._blockTillMove()\n")
            self.__tellEngineToMoveNow()
            self._blockTillMove()
        
        for i in xrange(moves):
            print >> self.engine, "undo"
        
        if gamemodel.curplayer == self:
            self.board = gamemodel.boards[-1]
            self.__tellEngineToPlayCurrentColorAndMakeMove()
        else:
            self.board = None
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offer (self, offer):
        if offer.type == DRAW_OFFER:
            if self.features["draw"]:
                print >> self.engine, "draw"
        else:
            self.emit("accept", offer)
    
    def offerError (self, offer, error):
        if self.features["draw"]:
            # We don't keep track if engine draws are offers or accepts. We just
            # Always assume they are accepts, and if they are not, we get this
            # error and emit offer instead
            if offer.type == DRAW_OFFER and error == ACTION_ERROR_NONE_TO_ACCEPT:
                self.emit("offer", Offer(DRAW_OFFER))
    
    #===========================================================================
    #    Internal
    #===========================================================================
    
    def __usermove (self, board, move):
        if self.features["usermove"]:
            self.engine.write("usermove ")
        
        if self.features["san"]:
            print >> self.engine, toSAN(board, move)
        else: print >> self.engine, toAN(board, move, short=True)
    
    def __tellEngineToMoveNow (self):
        if self.features["sigint"]:
            self.engine.sigint()
        print >> self.engine, "?"
    
    def __tellEngineToStopPlayingCurrentColor (self):
        print >> self.engine, "force"
        self.engineIsInNotPlaying = True
    
    def __tellEngineToPlayCurrentColorAndMakeMove (self):
        print >> self.engine, "go"
        self.engineIsInNotPlaying = False
    
    def __sendAnalyze (self, inverse=False):
        self.__tellEngineToStopPlayingCurrentColor()
        
        if inverse:
            self.board = self.board.setColor(1-self.color)
            self.__printColor()
            self.mode = INVERSE_ANALYZING
        else:
            self.mode = ANALYZING
        
        print >> self.engine, "post"
        print >> self.engine, "analyze"
        
        # workaround for crafty not sending analysis after it has found a mating line
        # http://code.google.com/p/pychess/issues/detail?id=515
        if "crafty" in self.features["myname"].lower():
            print >> self.engine, "noise 0"
    
    def __printColor (self):
        #if self.features["colors"]:
        if self.board.color == WHITE:
            print >> self.engine, "white"
        else: print >> self.engine, "black"
        if self.engineIsInNotPlaying: print >> self.engine, "force"
        #elif self.features["playother"]:
        #    print >> self.engine, "playother"
    
    def __setBoard (self, board):
        if self.features["setboard"]:
            self.__tellEngineToStopPlayingCurrentColor()
            print >> self.engine, "setboard", board.asFen()
        else:
            # Kludge to set black to move, avoiding the troublesome and now
            # deprecated "black" command. - Equal to the one xboard uses
            self.__tellEngineToStopPlayingCurrentColor()
            if board.color == BLACK:
                print >> self.engine, "a2a3"
            print >> self.engine, "edit"
            print >> self.engine, "#"
            for color in WHITE, BLACK:
                for y, row in enumerate(board.data):
                    for x, piece in enumerate(row):
                        if not piece or piece.color != color:
                            continue
                        sign = reprSign[piece.sign]
                        cord = repr(Cord(x,y))
                        print >> self.engine, sign+cord
                print >> self.engine, "c"
            print >> self.engine, "."
    
    def _blockTillMove (self):
        saved_state = self.boardLock._release_save()
        log.debug("_blockTillMove(): acquiring self.movecon lock\n", self.defname)
        self.movecon.acquire()
        log.debug("_blockTillMove(): self.movecon acquired\n", self.defname)
        try:
            log.debug("_blockTillMove(): doing self.movecon.wait\n", self.defname)
            self.movecon.wait()
        finally:
            log.debug("_blockTillMove(): releasing self.movecon..\n", self.defname)
            self.movecon.release()
            self.boardLock._acquire_restore(saved_state)
    
    #===========================================================================
    #    Parsing
    #===========================================================================
    
    def parseLines (self, engine, lines):
        for line in lines:
            self.__parseLine(line)
    
    def __parseLine (self, line):
#        log.debug("__parseLine: line=\"%s\"\n" % line.strip(), self.defname)
        parts = whitespaces.split(line.strip())
        
        if parts[0] == "pong":
            self.lastpong = int(parts[1])
            return
        
        # Illegal Move
        if parts[0].lower().find("illegal") >= 0:
            log.warn("__parseLine: illegal move: line=\"%s\", board=%s" \
                % (line.strip(), self.board), self.defname)
            if parts[-2] == "sd" and parts[-1].isdigit():
                print >> self.engine, "depth", parts[-1] 
            return
        
        # A Move (Perhaps)
        if self.board:
            if parts[0] == "move":
                movestr = parts[1]
            # Old Variation
            elif d_plus_dot_expr.match(parts[0]) and parts[1] == "...":
                movestr = parts[2]
            else:
                movestr = False
            
            if movestr:
                log.debug("__parseLine: acquiring self.boardLock\n", self.defname)
                self.waitingForMove = False
                self.readyForMoveNowCommand = False
                self.boardLock.acquire()
                try:
                    if self.engineIsInNotPlaying:
                        # If engine was set in pause just before the engine sent its
                        # move, we ignore it. However the engine has to know that we
                        # ignored it, and thus we step it one back
                        log.log("__parseLine: Discarding engine's move: %s\n" % movestr, self.defname)
                        print >> self.engine, "undo"
                        return
                    else:
                        try:
                            move = parseAny(self.board, movestr)
                        except ParsingError, e:
                            raise PlayerIsDead, e
                        
                        if validate(self.board, move):
                            self.board = None
                            self.returnQueue.put(move)
                            return
                        raise PlayerIsDead, "Board didn't validate after move"
                finally:
                    log.debug("__parseLine(): releasing self.boardLock\n", self.defname)
                    self.boardLock.release()
                    self.movecon.acquire()
                    self.movecon.notifyAll()
                    self.movecon.release()
        
        # Analyzing
        if self.engineIsInNotPlaying:
            if parts[:4] == ["0","0","0","0"]:
                # Crafty doesn't analyze until it is out of book
                print >> self.engine, "book off"
                return
            
            match = anare.match(line)
            if match:
                score, moves = match.groups()
                
                if "mat" in score.lower():
                    # Will look either like -Mat 3 or Mat3
                    scoreval = MATE_VALUE - int("".join(c for c in score if c.isdigit()))
                    if score.startswith('-'): scoreval = -scoreval
                else:
                    scoreval = int(score)
                
                mvstrs = movere.findall(moves)
                try:
                    moves = listToMoves (self.board, mvstrs, type=None, validate=True, ignoreErrors=False)
                except ParsingError, e:
                    # ParsingErrors may happen when parsing "old" lines from
                    # analyzing engines, which haven't yet noticed their new tasks
                    log.debug("Ignored a line from analyzer: ParsingError%s\n" % e, self.defname)
                    return
                
                # Don't emit if we weren't able to parse moves, or if we have a move
                # to kill the opponent king - as it confuses many engines
                if moves and not self.board.board.opIsChecked():
                    self.emit("analyze", moves, scoreval)
                
                return
        
        # Offers draw
        if parts[0:2] == ["offer", "draw"]:
            self.emit("accept", Offer(DRAW_OFFER))
            return
        
        # Resigns
        if "resign" in parts:
            self.emit("offer", Offer(RESIGNATION))
            return
        
        #if parts[0].lower() == "error":
        #    return
        
        #Tell User Error
        if parts[0] == "tellusererror":
            log.warn("Ignoring tellusererror: %s\n" % " ".join(parts[1:]))
            return
        
        # Tell Somebody
        if parts[0][:4] == "tell" and \
                parts[0][4:] in ("others", "all", "ics", "icsnoalias"):
            
            # Crafty sometimes only resign to ics :S
            #if parts[1] == "resign":
            #    self.emit("offer", Offer(RESIGNATION))
            #    log.warn("Interpreted tellics as a wish to resign")
            #else:
            log.log("Ignoring tell %s: %s\n" % (parts[0][4:], " ".join(parts[1:])))
            return
        
        if "feature" in parts:
            # We skip parts before 'feature', as some engines give us lines like
            # White (1) : feature setboard=1 analyze...e="GNU Chess 5.07" done=1
            parts = parts[parts.index("feature"):]
            for i, pair in enumerate(parts[1:]):
                
                # As "parts" is split with no thoughs on quotes or double quotes
                # we need to do some extra handling.
                
                if pair.find("=") < 0: continue
                key, value = pair.split("=",1)
                
                if value[0] in ('"',"'") and value[-1] in ('"',"'"):
                    value = value[1:-1]
                
                # If our pair was unfinished, like myname="GNU, we search the
                # rest of the pairs for a quotating mark.
                elif value[0] in ('"',"'"):
                    rest = value[1:] + " " + " ".join(parts[2+i:])
                    i = rest.find('"')
                    j = rest.find("'")
                    if i + j == -2:
                        log.warn("Missing endquotation in %s feature", self.defname)
                        value = rest
                    elif min(i, j) != -1:
                        value = rest[:min(i, j)]
                    else:
                        l = max(i, j)
                        value = rest[:l]
                
                else:
                    # All nonquoted values are ints
                    value = int(value)
                
                if key == "done":
                    if value == 1:
                        self.emit("readyForOptions")
                        self.emit("readyForMoves")
                        self.returnQueue.put("ready")
                    elif value == 0:
                        log.log("Adds %d seconds timeout\n" % TIME_OUT_SECOND, self.defname)
                        # This'll buy you some more time
                        self.timeout = time.time()+TIME_OUT_SECOND
                        self.returnQueue.put("not ready")
                    return
                
                self.features[key] = value
        
        # A hack to get better names in protover 1.
        # Unfortunately it wont work for now, as we don't read any lines from
        # protover 1 engines. When should we stop?
        if self.protover == 1:
            if self.defname[0] in ''.join(parts):
                basis = self.defname[0]
                name = ' '.join(itertools.dropwhile(lambda part: basis not in part, parts))
                self.features['myname'] = name
        
    
    #===========================================================================
    #    Info
    #===========================================================================
    
    def setName (self, name):
        self.name = name
    
    def canAnalyze (self):
        assert self.ready, "Still waiting for done=1"
        return self.features["analyze"]
    
    def isAnalyzing (self):
        return self.mode in (ANALYZING, INVERSE_ANALYZING)
    
    def __repr__ (self):
        if self.name:
            return self.name
        return self.features["myname"]
