""" This is a dictionary, that supports a max of items.
    This is good for the transportation table, as some old entries might not
    be useable any more, as the position has totally changed """

from UserDict import UserDict
from const import hashfALPHA, hashfBETA, hashfEXACT

class TranspositionTable (UserDict):
    def __init__ (self, maxSize):
        UserDict.__init__(self)
        assert maxSize > 0
        self.maxSize = maxSize
        self.krono = []
        self.maxdepth = 0
        
    def __setitem__ (self, key, item):
        if not key in self:
            if len(self) >= self.maxSize:
                try:
                    del self[self.krono[0]]
                except KeyError: pass # Overwritten
                del self.krono[0]
        self.data[key] = item
        self.krono.append(key)
    
    def probe (self, board, depth, alpha, beta):
        if not board in self: return
        entries = self[board]
        for d in xrange(self.maxdepth, depth-1, -1):
            if not d in entries: continue
            moves, score, hashf = entries[d]
            if hashf == hashfEXACT:
                return moves, score
            if hashf == hashfALPHA and score <= alpha:
                return moves, alpha
            if hashf == hashfBETA and score >= beta:
                return moves, beta
            return
        
    def record (self, board, moves, depth, score, hashf):
        if board in self:
            self[board][depth] = (moves, score, hashf)
        else: self[board] = {depth:(moves, score, hashf)}
        if depth > self.maxdepth: self.maxdepth = depth
