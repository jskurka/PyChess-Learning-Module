from UserDict import UserDict
from pychess.Utils.const import hashfALPHA, hashfBETA, hashfEXACT, WHITE
from ldata import MATE_VALUE
from pychess.System.LimitedDict import LimitedDict
from types import InstanceType

class TranspositionTable:
    def __init__ (self, maxSize):
        assert maxSize > 0
        self.data = {}
        self.maxSize = maxSize
        self.krono = []
        
        self.killer1 = [-1]*20
        self.killer2 = [-1]*20
        self.hashmove = [-1]*20
    
    def clear (self):
        self.data.clear()
        del self.krono[:]
        self.killer1 = [-1]*20
        self.killer2 = [-1]*20
        self.hashmove = [-1]*20
    
    def probe (self, board, depth, alpha, beta):
        assert type(board) == InstanceType, type(board)
        try:
            move, score, hashf, ply = self.data[board.hash]
            if ply < depth:
                return
            if hashf == hashfEXACT:
                return move, score, hashf
            if hashf == hashfALPHA and score <= alpha:
                return move, alpha, hashf
            if hashf == hashfBETA and score >= beta:
                return move, beta, hashf
        except KeyError:
            return
    
    def record (self, board, move, score, hashf, ply):
        assert type(board) == InstanceType, type(board)
        
        if not board.hash in self.data:
            if len(self.data) >= self.maxSize:
                try:
                    del self.data[self.krono[0]]
                except KeyError: pass # Overwritten
                del self.krono[0]
        self.data[board.hash] = (move, score, hashf, ply)
        self.krono.append(board.hash)
    
    def addKiller (self, ply, move):
        if self.killer1[ply] == -1:
            self.killer1[ply] = move
        elif move != self.killer1[ply]:
            self.killer2[ply] = move
    
    def isKiller (self, ply, move):
        if self.killer1[ply] == move:
            return 10
        elif self.killer2[ply] == move:
            return 8
        if ply >= 2:
            if self.killer1[ply-2] == move:
                return 6
            elif  self.killer2[ply-2] == move:
                return 4
        return 0
    
    def setHashMove (self, ply, move):
        self.hashmove[ply] = move
    
    def isHashMove (self, ply, move):
        return self.hashmove[ply] == move
