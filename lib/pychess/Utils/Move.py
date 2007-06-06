#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from pychess.Utils.Cord import Cord
from pychess.Utils.const import *
from lutils import lmove
from lutils.lmove import ParsingError, FLAG_PIECE

class Move:
    
    def __init__ (self, cord0, cord1=None, board=None, promotion=None):
        """ Inits a new highlevel Move object.
            The object can be initialized in the follow ways:
                Move(cord0, cord1, board, [promotionPiece])
                Move(lovLevelMoveInt) """
        
        if not cord1:
            self.move = cord0
            flag = self.move >> 12
            if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                        BISHOP_PROMOTION, KNIGHT_PROMOTION):
                self.promotion = lmove.PROMOTE_PIECE (self.move)
            else: self.promotion = QUEEN
            self.cord0 = Cord(lmove.FCORD(self.move))
            self.cord1 = Cord(lmove.TCORD(self.move))
            
        else:
            self.cord0 = cord0
            self.cord1 = cord1
            
            flag = NORMAL_MOVE
            
            if board[self.cord0].piece == PAWN and  self.cord1.y in (0,7):
                if promotion == None: promotion = QUEEN
                flag = FLAG_PIECE(promotion)
            
            elif board[self.cord0].piece == KING:
                if self.cord0.x - self.cord1.x == 2:
                    flag = QUEEN_CASTLE
                elif self.cord0.x - self.cord1.x == -2:
                    flag = KING_CASTLE
            
            elif board[self.cord0].piece == PAWN and \
                    board[self.cord1] == None and \
                    self.cord0.x != self.cord1.x and \
                    self.cord0.y != self.cord1.y:
                flag = ENPASSANT
            
            self.move = lmove.newMove(self.cord0.cord, self.cord1.cord, flag)
            
    def _get_cords (self):
        return (self.cord0, self.cord1)
    cords = property(_get_cords)
    
    def _get_promotion (self):
        flag = lmove.FLAG(self.move)
        if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                    BISHOP_PROMOTION, KNIGHT_PROMOTION):
            return lmove.PROMOTE_PIECE(flag)
        return None
    promotion = property(_get_promotion)
    
    def __repr__ (self):
        return str(self.cord0) + str(self.cord1)

    def __eq__ (self, other):
        if isinstance(other, Move):
            return self.move == other.move
    
    def __hash__ (self):
        return hash(self.cords)

################################################################################
# Parsers                                                                      #
################################################################################

def listToMoves (board, mstrs, type=None, validate=False):
	return [Move(move) for move in lmove.listToMoves(
	                                        board.board, mstrs, type, validate)]

def parseAny (board, algnot):
    return Move(lmove.parseAny (board.board, algnot))

def parseSAN (board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    
    return Move (lmove.parseSAN (board.board, san))

def parseLAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    return Move (lmove.parseLAN (board.board, lan))

def parseFAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    return Move (lmove.parseFAN (board.board, lan))

def parseAN (board, an):
    """ Parse an Algebraic Notation string """
    
    return Move(lmove.parseAN (board.board, an))

################################################################################
# Exporters                                                                    #
################################################################################

def listToSan (board, moves):
    return lmove.listToSan(board.board, [m.move for m in moves])

def toAN (board, move):
    """ Returns a Algebraic Notation string of a move
        board should be prior to the move """
    
    return lmove.toAN (board.board, move.move)
    
def toSAN (board, move):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move 
        The board should be prior to the move, board2 past.
        If not board2, toSAN will not test mate """
    
    return lmove.toSAN (board.board, move.move)

def toLAN (board, move):
    """ Returns a Long/Expanded Algebraic Notation string of a move
        board should be prior to the move """
    
    return lmove.toLAN (board.board, move.move)

def toFAN (board, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    
    return lmove.toFAN (board.board, move.move)
