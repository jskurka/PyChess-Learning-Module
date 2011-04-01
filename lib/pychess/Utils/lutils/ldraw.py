from bitboard import bitLength
from ldata import BLACK_SQUARES
from pychess.Utils.const import *

def repetitionCount (board, drawThreshold=3):
    rc = 1
    for ply in xrange(4, 1+min(len(board.history), board.fifty), 2):
        if board.history[-ply][4] == board.hash:
            rc += 1
            if rc >= drawThreshold: break
    return rc

def testFifty (board):
    if board.fifty >= 100:
        return True
    return False

drawSet = set((
    (0, 0, 0, 0,   0, 0, 0, 0), #KK
    (0, 1, 0, 0,   0, 0, 0, 0), #KBK
    (1, 0, 0, 0,   0, 0, 0, 0), #KNK
    (0, 0, 0, 0,   0, 1, 0, 0), #KKB
    (0, 0, 0, 0,   1, 0, 0, 0), #KNK
    
    (1, 0, 0, 0,   0, 1, 0, 0), #KNKB
    (0, 1, 0, 0,   1, 0, 0, 0), #KBKN
))

# Contains not 100% sure ones 
drawSet2 = set((
    (2, 0, 0, 0,   0, 0, 0, 0), #KNNK
    (0, 0, 0, 0,   2, 0, 0, 0), #KKNN
    
    (2, 0, 0, 0,   1, 0, 0, 0), #KNNKN
    (1, 0, 0, 0,   2, 0, 0, 0), #KNKNN
    (2, 0, 0, 0,   0, 1, 0, 0), #KNNKB
    (0, 1, 0, 0,   2, 0, 0, 0), #KBKNN
    (2, 0, 0, 0,   0, 0, 1, 0), #KNNKR
    (0, 0, 1, 0,   2, 0, 0, 0)  #KRKNN
))

def testMaterial (board):
    """ Tests if no players are able to win the game from the current
        position """
    
    whiteBoards = board.boards[WHITE]
    blackBoards = board.boards[BLACK]
    
    if bitLength(whiteBoards[PAWN]) or bitLength(blackBoards[PAWN]):
        return False
    
    if bitLength(whiteBoards[QUEEN]) or bitLength(blackBoards[QUEEN]):
        return False
    
    wn = bitLength(whiteBoards[KNIGHT])
    wb = bitLength(whiteBoards[BISHOP])
    wr = bitLength(whiteBoards[ROOK])
    bn = bitLength(blackBoards[KNIGHT])
    bb = bitLength(blackBoards[BISHOP])
    br = bitLength(blackBoards[ROOK])
    
    if (wn, wb, wr, 0,   bn, bb, br, 0) in drawSet:
        return True
        
    # Tests KBKB. Draw if bishops are of same color
    if not wn + wr + bn + wr and wb == 1 and bb == 1:
        if whiteBoards[BISHOP] & BLACK_SQUARES and True != \
           blackBoards[BISHOP] & BLACK_SQUARES and True:
            return True

def testPlayerMatingMaterial (board, color):
    """ Tests if given color has enough material to mate on board """

    boards = board.boards[color]
    
    if bitLength(boards[PAWN]) or bitLength(boards[QUEEN]) \
       or bitLength(boards[ROOK]) \
       or (bitLength(boards[KNIGHT]) + bitLength(boards[BISHOP]) > 1):
        return True
    return False

# This could be expanded by the fruit kpk draw function, which can test if a
# certain king verus king and pawn posistion is winable.

def test (board):
    """ Test if the position is drawn. Two-fold repetitions are counted. """
    return repetitionCount (board, drawThreshold=2) > 1 or \
           testFifty (board) or \
           testMaterial (board)
