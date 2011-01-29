from const import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from const import reprSign, reprColor, reprPiece

class Piece:
    def __init__ (self, color, piece):
        self.color = color
        self.piece = piece
    	
    	self.opacity = 1.0
    	self.x = None
    	self.y = None
    
    # Sign is a deprecated synonym for piece
    def _set_sign (self, sign):
        self.piece = sign
    def _get_sign (self):
        return self.piece
    sign = property(_get_sign, _set_sign)
    
    def __repr__ (self):
        represen = "<%s %s" % (reprColor[self.color], reprPiece[self.piece])
        if self.opacity != 1.0:
            represen += " Op:%0.1f" % self.opacity
        if self.x != None or self.y != None:
            if self.x != None:
                represen += " X:%0.1f" % self.x
            else: represen += " X:None"
            if self.y != None:
                represen += " Y:%0.1f" % self.y
            else: represen += " Y:None"
        represen += ">"
        return represen
