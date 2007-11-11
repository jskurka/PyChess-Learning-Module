# -*- coding: UTF-8 -*-

################################################################################
# PyChess information                                                          #
################################################################################

NAME = "PyChess"
VERSION = "0.8beta1"
VERSION_NAME = "Philidor"

################################################################################
# Player info                                                                  #
################################################################################

# Player types
LOCAL, ARTIFICIAL, REMOTE = range(3)

# Engine strengths
EASY, INTERMEDIATE, EXPERT = range(3)

# Player colors
WHITE, BLACK = range(2)
reprColor = [_("White"), _("Black")]

################################################################################
# Game values                                                                  #
################################################################################

# Game states
WAITING_TO_START, PAUSED, RUNNING, DRAW, WHITEWON, BLACKWON, KILLED, \
    ADJOURNED, ABORTED, UNKNOWN_STATE = range(10)
reprResult = ["*", "*", "*", "1/2-1/2", "1-0", "0-1", "?", "*", "?", "?"]

# Action errors
ACTION_ERROR_NO_CLOCK, ACTION_ERROR_NOT_OUT_OF_TIME, \
    ACTION_ERROR_CLOCK_NOT_STARTED, ACTION_ERROR_SWITCH_UNDERWAY, \
    ACTION_ERROR_CLOCK_NOT_PAUSED, ACTION_ERROR_TO_LARGE_UNDO, \
    ACTION_ERROR_NONE_TO_ACCEPT, ACTION_ERROR_NONE_TO_WITHDRAW, \
    ACTION_ERROR_NONE_TO_DECLINE = range(9)

# Game state reasons
ABORTED_ADJUDICATION, ABORTED_AGREEMENT, ABORTED_COURTESY, ABORTED_EARLY, \
    ABORTED_SERVER_SHUTDOWN, \
ADJOURNED_AGREEMENT, ADJOURNED_LOST_CONNECTION, ADJOURNED_SERVER_SHUTDOWN, \
DRAW_50MOVES, DRAW_ADJUDICATION, DRAW_AGREE, DRAW_CALLFLAG, DRAW_INSUFFICIENT, \
    DRAW_LENGTH, DRAW_REPITITION, DRAW_STALEMATE, \
WON_ADJUDICATION, WON_CALLFLAG, WON_DISCONNECTION, WON_MATE, WON_RESIGN, \
WHITE_ENGINE_DIED, BLACK_ENGINE_DIED, UNKNOWN_REASON = range(24)

# Player actions
RESIGNATION, FLAG_CALL, DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER, PAUSE_OFFER, \
    RESUME_OFFER, SWITCH_OFFER, TAKEBACK_OFFER, TAKEBACK_FORCE, HURRY_REQUEST \
    = range(11)
OFFERS = set([DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER, PAUSE_OFFER, \
    RESUME_OFFER, SWITCH_OFFER, TAKEBACK_OFFER])

# A few nice to have boards
FEN_EMPTY = "8/8/8/8/8/8/8/8 w KQkq - 0 1"
FEN_START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

################################################################################
# Search values                                                                #
################################################################################

hashfALPHA, hashfBETA, hashfEXACT = range(3)

# Engine modes
NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)

################################################################################
# Piece types                                                                  #
################################################################################

# BPAWN is a pawn that moves in the opposite direction
EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, BPAWN = range(8)
reprPiece = ["Empty", _("Pawn"), _("Knight"), _("Bishop"), _("Rook"), _("Queen"), _("King"), "BPawn"]

# Is sliding piece
sliders = [ False, False, False, True, True, True, False, False ]

# Piece signs
reprSign = ["", "P", "N", "B", "R", "Q", "K"]
chr2Sign = {"k":KING, "q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT, "p":PAWN}
localReprSign = ["", _("P"), _("N"), _("B"), _("R"), _("Q"), _("K")]

################################################################################
# Move values                                                                  #
################################################################################

NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, ENPASSANT, \
KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION = range(8)

PROMOTIONS = (QUEEN_PROMOTION, ROOK_PROMOTION, BISHOP_PROMOTION, KNIGHT_PROMOTION)
# Algebraic notation types: Short, Long, Figure and Simpe
SAN, LAN, FAN, AN = range(4)

FAN_PIECES = [
    ["", "♙", "♘", "♗", "♖", "♕", "♔", ""],
    ["", "♟", "♞", "♝", "♜", "♛", "♚", ""]
]

################################################################################
# Castling values                                                              #
################################################################################
W_OO, W_OOO, B_OO, B_OOO = [2**i for i in range(4)]
W_CASTLED, B_CASTLED = [2**i for i in range(2)]

################################################################################
# Cords types                                                                  #
################################################################################

A1, B1, C1, D1, E1, F1, G1, H1, \
A2, B2, C2, D2, E2, F2, G2, H2, \
A3, B3, C3, D3, E3, F3, G3, H3, \
A4, B4, C4, D4, E4, F4, G4, H4, \
A5, B5, C5, D5, E5, F5, G5, H5, \
A6, B6, C6, D6, E6, F6, G6, H6, \
A7, B7, C7, D7, E7, F7, G7, H7, \
A8, B8, C8, D8, E8, F8, G8, H8 = range (64)

reprCord = [
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
    "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
    "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
    "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
    "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
    "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
    "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
    "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8"
]

reprFile = ["a", "b", "c", "d", "e", "f", "g", "h"]
reprRank = ["1", "2", "3", "4", "5", "6", "7", "8"]

cordDic = {}
for cord, name in enumerate(reprCord):
    cordDic[name] = cord

################################################################################
# Internet Chess                                                               #
################################################################################

IC_CONNECTED, IC_DISCONNECTED = range(2)

IC_POS_ISOLATED, IC_POS_OBSERVING_EXAMINATION, IC_POS_EXAMINATING, \
IC_POS_OP_TO_MOVE, IC_POS_ME_TO_MOVE, IC_POS_OBSERVING = range(6)

################################################################################
# User interface                                                               #
################################################################################

# Hint modes
HINT, SPY = ["hint", "spy"]

# Sound settings
SOUND_MUTE, SOUND_BEEP, SOUND_SELECT, SOUND_URI = range(4)

# Brush types. Send piece object for Piece brush
CLEAR, ENPAS = range(2)

from os import getuid
from pwd import getpwuid
userdata = getpwuid(getuid())
i = userdata.pw_gecos.find(',')
if i >= 0:
    username = userdata.pw_gecos[i:]
else: username = userdata.pw_name
del userdata, i

################################################################################
# Subprocess types                                                             #
################################################################################

SUBPROCESS_PTY, SUBPROCESS_SUBPROCESS, SUBPROCESS_FORK = range(3)
