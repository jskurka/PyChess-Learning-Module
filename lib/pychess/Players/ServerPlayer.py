
from Queue import Queue

from Player import Player, PlayerIsDead, TurnInterrupt
from pychess.Utils.Offer import Offer
from pychess.Utils.Move import parseSAN, toSAN, ParsingError
from pychess.Utils.const import *
from pychess.ic import telnet

class ServerPlayer (Player):
    __type__ = REMOTE
    
    def __init__ (self, boardmanager, offermanager,
                        name, external, gameno, color):
        Player.__init__(self)
        
        self.queue = Queue()
        
        self.name = name
        self.color = color
        self.gameno = gameno
        
        # If we are not playing against a player on the users computer. E.g.
        # when we observe a game on FICS. In these cases we don't send anything
        # back to the server.
        self.external = external
        
        self.boardmanager = boardmanager
        self.boardmanager.connect("moveRecieved", self.moveRecieved)
        self.offermanager = offermanager
        self.offermanager.connect("onOfferAdd", self.onOfferAdd)
        self.offermanager.connect("onOfferRemove", self.onOfferRemove)
        
        self.offerToIndex = {}
        self.indexToOffer = {}
        self.lastPly = -1
    
    def onOfferAdd (self, om, index, offer):
        self.indexToOffer[index] = offer
        self.emit ("offer", offer)
    
    def onOfferRemove (self, om, index):
        if index in self.indexToOffer:
            self.emit ("withdraw", self.indexToOffer[index])
    
    def offer (self, offer):
        self.offermanager.offer(offer, self.lastPly)
    
    def offerDeclined (self, offer):
        pass
    
    def offerWithdrawn (self, offer):
        pass
    
    def offerError (self, offer, error):
        pass
    
    def moveRecieved (self, bm, ply, sanmove, gameno, curcol):
        self.lastPly = int(ply)
        if curcol != self.color or gameno != self.gameno:
            return
        print sanmove
        self.queue.put((ply,sanmove))
    
    def makeMove (self, gamemodel):
        self.lastPly = gamemodel.ply
        if gamemodel.moves and not self.external:
            self.boardmanager.sendMove (
                    toSAN (gamemodel.boards[-2], gamemodel.moves[-1]))
        
        item = self.queue.get(block=True)
        if item == "del":
            raise PlayerIsDead
        if item == "int":
            raise TurnInterrupt
        
        ply, sanmove = item
        if ply < gamemodel.ply:
            # This should only happen in an observed game
            self.emit("offer", Offer(TAKEBACK_FORCE, ply))
        
        try:
            move = parseSAN (gamemodel.boards[-1], sanmove)
        except ParsingError, e:
            print "Error", e.args[0]
            raise PlayerIsDead
        return move
    
    def __repr__ (self):
        return self.name
    
    
    def pause (self):
        pass
    
    def resume (self):
        pass
    
    def setBoard (self, fen):
        # setBoard will currently only be called for ServerPlayer when starting
        # to observe some game. In this case FICS already knows how the board
        # should look, and we don't need to set anything
        pass
    
    def end (self, status, reason):
        self.queue.put("del")
    
    def kill (self, reason):
        self.queue.put("del")
    
    def undoMoves (self, movecount, gamemodel):
        # If current player has changed so that it is no longer us to move,
        # We raise TurnInterruprt in order to let GameModel continue the game
        if movecount % 2 == 1 and gamemodel.curplayer != self:
            self.queue.put("int")
