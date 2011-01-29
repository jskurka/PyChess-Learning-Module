from array import array
from operator import or_
from pychess.Utils.const import *
#from pychess.Utils.lutils.lmove import RANK, FILE
from bitboard import *
def RANK (cord): return cord >> 3
def FILE (cord): return cord & 7
################################################################################
################################################################################
##   Evaluating constants                                                     ##
################################################################################
################################################################################

PAWN_VALUE = 100
KNIGHT_VALUE = 300
BISHOP_VALUE = 330
ROOK_VALUE = 500
QUEEN_VALUE = 900
KING_VALUE = 2000
PIECE_VALUES = [0, PAWN_VALUE, KNIGHT_VALUE,
                BISHOP_VALUE, ROOK_VALUE, QUEEN_VALUE, KING_VALUE]

MATE_VALUE = MAXVAL = 99999

# How many points does it give to have the piece standing i cords from the
# opponent king
pawnTScale = [0, 40, 20, 12, 9, 6, 4, 2, 1, 0]
bishopTScale = [0, 50, 25, 15, 7, 5, 3, 2, 2, 1]
knightTScale = [0, 100, 50, 35, 10, 3, 2, 2, 1, 1]
rookTScale = [0, 50, 40, 15, 5, 2, 1, 1, 1, 0]
queenTScale = [0, 100, 60, 20, 10, 7, 5, 4, 3, 2]

passedScores = (
    ( 0, 48, 48, 120, 144, 192, 240, 0 ),
    ( 0, 240, 192, 144, 120, 48, 48, 0 )
)

# Penalties for one or more isolated pawns on a given file 
isolani_normal = ( -8, -10, -12, -14, -14, -12, -10, -8 )
# Penalties if the file is half-open (i.e. no enemy pawns on it)
isolani_weaker = ( -22, -24, -26, -28, -28, -26, -24, -22 )

###############################################################################
# Distance boards for different pieces                                        #
###############################################################################

taxicab = [[0]*64 for i in range(64)]
sdistance = [[0]*64 for i in range(64)]
for fcord in xrange(64):
    for tcord in xrange(fcord+1, 64):
        fx = FILE(fcord) 
        fy = RANK(fcord)
        tx = FILE(tcord)
        ty = RANK(tcord)
        taxicab[fcord][tcord] = taxicab[fcord][tcord] = abs(fx-tx) + abs(fy-ty)
        sdistance[fcord][tcord] = sdistance[fcord][tcord] = min(abs(fx-tx), abs(fy-ty))

distance = [[[0]*64 for i in xrange(64)] for j in xrange(KING+1)]

distance[EMPTY] = None
distance[KING] = sdistance
distance[PAWN] = sdistance

# Special table for knightdistances

knightDistance = [
    6, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 6,
    5, 4, 5, 4, 3, 4, 3, 4, 3, 4, 3, 4, 5, 4, 5,
    4, 5, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 5, 4,
    5, 4, 3, 4, 3, 2, 3, 2, 3, 2, 3, 4, 3, 4, 5,
    4, 3, 4, 3, 2, 3, 2, 3, 2, 3, 2, 3, 4, 3, 4,
    5, 4, 3, 2, 3, 4, 1, 2, 1, 4, 3, 2, 3, 4, 5,
    4, 3, 4, 3, 2, 1, 2, 3, 2, 1, 2, 3, 4, 3, 4,
    5, 4, 3, 2, 3, 2, 3, 0, 3, 2, 3, 2, 3, 4, 5,
    4, 3, 4, 3, 2, 1, 2, 3, 2, 1, 2, 3, 4, 3, 4,
    5, 4, 3, 2, 3, 4, 1, 2, 1, 4, 3, 2, 3, 4, 5,
    4, 3, 4, 3, 2, 3, 2, 3, 2, 3, 2, 3, 4, 3, 4,
    5, 4, 3, 4, 3, 2, 3, 2, 3, 2, 3, 4, 3, 4, 5,
    4, 5, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 5, 4,
    5, 4, 5, 4, 3, 4, 3, 4, 3, 4, 3, 4, 5, 4, 5,
    6, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 6,
]

# Calculate

for fcord in xrange(64):
    frank = RANK(fcord)
    ffile = FILE(fcord)
    
    for tcord in xrange(fcord+1, 64):
        # Notice, that we skip fcord == tcord, as all fields are zero from
        # scratch in anyway
        
        trank = RANK(tcord)
        tfile = FILE(tcord)
        
        # Knight
        field = (7-frank+trank)*15 + 7-ffile+tfile
        distance[KNIGHT][tcord][fcord] = distance[KNIGHT][fcord][tcord] = \
            knightDistance[field]
        
        # Rook
        if frank == trank or ffile == tfile:
            distance[ROOK][tcord][fcord] = distance[ROOK][fcord][tcord] = 1
        else: distance[ROOK][tcord][fcord] = distance[ROOK][fcord][tcord] = 2
        
        # Bishop
        if abs(frank-trank) == abs(ffile-tfile):
            distance[BISHOP][tcord][fcord] = distance[BISHOP][fcord][tcord] = 1
        else: distance[BISHOP][tcord][fcord] = distance[BISHOP][fcord][tcord] = 2
        
        # Queen
        if frank == trank or ffile == tfile or abs(frank-trank) == abs(ffile-tfile):
            distance[QUEEN][tcord][fcord] = distance[QUEEN][fcord][tcord] = 1
        else: distance[QUEEN][tcord][fcord] = distance[QUEEN][fcord][tcord] = 2

# Special cases for knights in corners
distance[KNIGHT][A1][B2] = distance[KNIGHT][B2][A1] = 4
distance[KNIGHT][H1][G2] = distance[KNIGHT][G2][H1] = 4
distance[KNIGHT][A8][B7] = distance[KNIGHT][B7][A8] = 4
distance[KNIGHT][H8][G7] = distance[KNIGHT][G7][H8] = 4

###############################################################################
# Boards used for evaluating
###############################################################################

pawnScoreBoard = (
   (0,  0,  0,  0,  0,  0,  0,  0,
    5,  5,  5,-10,-10,  5,  5,  5,
   -2, -2, -2,  6,  6, -2, -2, -2,
    0,  0,  0, 25, 25,  0,  0,  0,
    2,  2, 12, 16, 16, 12,  2,  2,
    4,  8, 12, 16, 16, 12,  4,  4,
    4,  8, 12, 16, 16, 12,  4,  4,
    0,  0,  0,  0,  0,  0,  0,  0),
    
   (0,  0,  0,  0,  0,  0,  0,  0,
    4,  8, 12, 16, 16, 12,  4,  4,
    4,  8, 12, 16, 16, 12,  4,  4,
    2,  2, 12, 16, 16, 12,  2,  2,
    0,  0,  0, 25, 25,  0,  0,  0,
   -2, -2, -2,  6,  6, -2, -2, -2,
    5,  5,  5,-10,-10,  5,  5,  5,
    0,  0,  0,  0,  0,  0,  0,  0)
)

outpost = (
   (0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 0, 0, 1, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0),
    
   (0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 1, 1, 0, 0, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0)
)

normalKing = (
   24, 24, 24, 16, 16,  0, 32, 32,
   24, 20, 16, 12, 12, 16, 20, 24,
   16, 12,  8,  4,  4,  8, 12, 16,
   12,  8,  4,  0,  0,  4,  8, 12,
   12,  8,  4,  0,  0,  4,  8, 12,
   16, 12,  8,  4,  4,  8, 12, 16,
   24, 20, 16, 12, 12, 16, 20, 24,
   24, 24, 24, 16, 16,  0, 32, 32
)

endingKing = (
   0,  6, 12, 18, 18, 12,  6,  0,
   6, 12, 18, 24, 24, 18, 12,  6,
  12, 18, 24, 32, 32, 24, 18, 12,
  18, 24, 32, 48, 48, 32, 24, 18,
  18, 24, 32, 48, 48, 32, 24, 18,
  12, 18, 24, 32, 32, 24, 18, 12,
   6, 12, 18, 24, 24, 18, 12,  6,
   0,  6, 12, 18, 18, 12,  6,  0
)

###############################################################################
# Maps for bitboards
###############################################################################

d2e2    = (createBoard(0x0018000000000000), createBoard(0x0000000000001800))
brank7  = (createBoard(0x000000000000FF00), createBoard(0x00FF000000000000))
brank8  = (createBoard(0x00000000000000FF), createBoard(0xFF00000000000000))
brank67 = (createBoard(0x0000000000FFFF00), createBoard(0x00FFFF0000000000))
brank58 = (createBoard(0x00000000FFFFFFFF), createBoard(0xFFFFFFFF00000000))
brank48 = (createBoard(0x000000FFFFFFFFFF), createBoard(0xFFFFFFFFFF000000))

# Penalties if the file is half-open (i.e. no enemy pawns on it)
isolani_weaker = (-22, -24, -26, -28, -28, -26, -24, -22)

stonewall = [createBoard(0), createBoard(0)]
# D4, E3, F4
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - # - # - -
# - - - - # - - -
# - - - - - - - -
# - - - - - - - -
stonewall[WHITE] = createBoard(0x81400000000)

# D5, E6, F5
# - - - - - - - -
# - - - - - - - -
# - - - - # - - -
# - - - # - # - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
stonewall[BLACK] = createBoard(0x81400000000)

# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - # - - - - # -
# # # - - - - # #
# - - - - - - - -
qwwingpawns1 = bitPosArray[A2] | bitPosArray[B2]
qwwingpawns2 = bitPosArray[A2] | bitPosArray[B3]
kwwingpawns1 = bitPosArray[G2] | bitPosArray[H2]
kwwingpawns2 = bitPosArray[G3] | bitPosArray[H2]

# - - - - - - - -
# # # - - - - # #
# - # - - - - # -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
qbwingpawns1 = bitPosArray[A7] | bitPosArray[B7]
qbwingpawns2 = bitPosArray[A7] | bitPosArray[B6]
kbwingpawns1 = bitPosArray[G7] | bitPosArray[H7]
kbwingpawns2 = bitPosArray[G6] | bitPosArray[H7]

################################################################################
#  Ranks and files                                                             #
################################################################################

rankBits = [createBoard(255 << i*8) for i in xrange(7,-1,-1)]
fileBits = [createBoard(0x0101010101010101 << i) for i in xrange(7,-1,-1)]

################################################################################
################################################################################
##   Bit boards                                                               ##
################################################################################
################################################################################

WHITE_SQUARES = createBoard(0x55AA55AA55AA55AA)
BLACK_SQUARES = createBoard(0xAA55AA55AA55AA55)

# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - # # - - -
# - - - # # - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
CENTER_FOUR = createBoard(0x0000001818000000)

# - - - - - - - -
# - - - - - - - -
# - - # # # # - -
# - - # # # # - -
# - - # # # # - -
# - - # # # # - -
# - - - - - - - -
# - - - - - - - -
sbox = createBoard(0x00003C3C3C3C0000)

# - - - - - - - -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - - - - - - - -
lbox = createBoard(0x007E7E7E7E7E7E00)

# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
right = fileBits[5] | fileBits[6] | fileBits[7]

# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
left = fileBits[0] | fileBits[1] | fileBits[2]

################################################################################
#  Generate the move bitboards.  For e.g. the bitboard for all                 #
#  the moves of a knight on f3 is given by MoveArray[knight][21].              #
################################################################################

dir = [
    None,
    [ 9, 11 ], # Only capture moves are included
    [ -21, -19, -12, -8, 8, 12, 19, 21 ],
    [ -11, -9, 9, 11 ],
    [ -10, -1, 1, 10 ],
    [ -11, -10, -9, -1, 1, 9, 10, 11 ],
    [ -11, -10, -9, -1, 1, 9, 10, 11 ],
    [ -9, -11 ],
    
    # Following are for front and back walls. Will be removed from list after
    # the loop
    [ 9, 10, 11],
    [ -9, -10, -11]
]

sliders += [False, False]

map = [
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1,  0,  1,  2,  3,  4,  5,  6,  7, -1,
    -1,  8,  9, 10, 11, 12, 13, 14, 15, -1,
    -1, 16, 17, 18, 19, 20, 21, 22, 23, -1,
    -1, 24, 25, 26, 27, 28, 29, 30, 31, -1,
    -1, 32, 33, 34, 35, 36, 37, 38, 39, -1,
    -1, 40, 41, 42, 43, 44, 45, 46, 47, -1,
    -1, 48, 49, 50, 51, 52, 53, 54, 55, -1,
    -1, 56, 57, 58, 59, 60, 61, 62, 63, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 
]

moveArray = [[createBoard(0)]*64 for i in xrange(len(dir))] # moveArray[8][64]

for piece in xrange(1,len(dir)):
    for fcord in xrange(120):
        f = map[fcord]
        if f == -1:
            # We only generate moves for squares inside the board
            continue
        # Create a new bitboard
        b = createBoard(0)
        for d in dir[piece]:
            tcord = fcord
            while True:
                tcord += d
                t = map[tcord]
                if t == -1:
                    # If we landed outside of board, there is no more to look
                    # for
                    break
                b = setBit (b, t)
                if not sliders[piece]:
                    # If we are a slider, we should not break, but add the dir
                    # value once again
                    break
        moveArray[piece][f] = b

frontWall = (moveArray[8], moveArray[9])
del moveArray[9]; del moveArray[8]
del dir[9]; del dir[8]
del sliders[9]; del sliders[8]

################################################################################
#  For each square, there are 8 rays.  The first 4 rays are diagonals          #
#  for the bishops and the next 4  are file/rank for the rooks.                #
#  The queen uses all 8 rays.                                                  #
#  These rays are used for move generation rather than MoveArray[].            #
#  Also initialize the directions[][] array.  directions[f][t] returns         #
#  the index into rays[f] array allow us to find the ray in that direction.    #
################################################################################

directions = [[-1]*64 for i in xrange(64)] # directions[64][64]
rays = [[createBoard(0)]*8 for i in xrange(64)] # rays[64][8]

for fcord in xrange(120):
    f = map[fcord]
    if f == -1: continue
    ray = -1
    for piece in BISHOP, ROOK:
        for d in dir[piece]:
            ray += 1
            b = 0
            tcord = fcord
            while True:
               tcord += d
               t = map[tcord]
               if t == -1:
                   break
               rays[f][ray] = setBit (rays[f][ray], t)
               directions[f][t] = ray

################################################################################
#  The FromToRay[b2][f6] gives the diagonal ray from c3 to f6;                 #
#  It also produces horizontal/vertical rays as well. If no                    #
#  ray is possible, then a 0 is returned.                                      #
################################################################################

fromToRay = [[createBoard(0)]*64 for i in xrange(64)] # fromToRay[64][64]

for piece in BISHOP, ROOK:
    for fcord in xrange (120):
        f = map[fcord]
        if f == -1: continue
        for d in dir[piece]:
            tcord = fcord
            t = map[tcord]
            
            while True:
                b = fromToRay[f][t]
                tcord += d
                t = map[tcord]
                if t == -1:
                    break
                fromToRay[f][t] = setBit (fromToRay[f][t], t)
                fromToRay[f][t] |= b

################################################################################
#  The PassedPawnMask variable is used to determine if a pawn is passed.       #
#  This mask is basically all 1's from the square in front of the pawn to      #
#  the promotion square, also duplicated on both files besides the pawn        #
#  file.  Other bits will be set to zero.                                      #
#  E.g. PassedPawnMask[white][b3] = 1's in a4-c4-c8-a8 rect, 0 otherwise.      #
################################################################################

passedPawnMask = [[createBoard(0)]*64, [createBoard(0)]*64]

#  Do for white pawns first
for cord in xrange(64):
    passedPawnMask[WHITE][cord] = rays[cord][7]
    passedPawnMask[BLACK][cord] = rays[cord][4]
    if cord & 7 != 0:
        #  If file is not left most
        passedPawnMask[WHITE][cord] |= rays[cord-1][7]
        passedPawnMask[BLACK][cord] |= rays[cord-1][4]
    if cord & 7 != 7:
        #  If file is not right most
        passedPawnMask[WHITE][cord] |= rays[cord+1][7]
        passedPawnMask[BLACK][cord] |= rays[cord+1][4]

################################################################################
#  The IsolaniMask variable is used to determine if a pawn is an isolani.      #
#  This mask is basically all 1's on files beside the file the pawn is on.     #
#  Other bits will be set to zero.                                             #
#  E.g. isolaniMask[d-file] = 1's in c-file & e-file, 0 otherwise.             #
################################################################################

isolaniMask = [0]*8

isolaniMask[0] = fileBits[1]
isolaniMask[7] = fileBits[6]
for i in xrange (1, 7):
    isolaniMask[i] = fileBits[i-1] | fileBits[i+1]

#===============================================================================
# The SquarePawnMask is used to determine if a king is in the square of
# the passed pawn and is able to prevent it from queening.  
# Caveat:  Pawns on 2nd rank have the same mask as pawns on the 3rd rank
# as they can advance 2 squares.
#===============================================================================

squarePawnMask = [[createBoard(0)]*64, [createBoard(0)]*64]
for cord in xrange(64):
    # White mask
    l = 7 - RANK(cord)
    i = max(cord & 56, cord-l)
    j = min(cord | 7, cord+l)
    for k in xrange(i, j+1):
        squarePawnMask[WHITE][cord] |= bitPosArray[k] | fromToRay[k][k|56]
    
    # Black mask
    l = RANK(cord)
    i = max(cord & 56, cord-l)
    j = min(cord | 7, cord+l)
    for k in xrange(i, j+1):
        squarePawnMask[BLACK][cord] |= bitPosArray[k] | fromToRay[k][k&7]

# For pawns on 2nd rank, they have same mask as pawns on 3rd rank
for cord in xrange(A2, H2+1):
    squarePawnMask[WHITE][cord] = squarePawnMask[WHITE][cord+8]
for cord in xrange(A7, H7+1):
    squarePawnMask[BLACK][cord] = squarePawnMask[BLACK][cord-8]

################################################################################
#  These tables are used to calculate rook, queen and bishop moves             #
################################################################################

ray00  = [rays[cord][5] | rays[cord][6] | 1<<(63-cord) for cord in xrange(64)]
ray45  = [rays[cord][0] | rays[cord][3] | 1<<(63-cord) for cord in xrange(64)]
ray90  = [rays[cord][4] | rays[cord][7] | 1<<(63-cord) for cord in xrange(64)]
ray135 = [rays[cord][1] | rays[cord][2] | 1<<(63-cord) for cord in xrange(64)]

attack00 = [{} for i in xrange(64)]
attack45 = [{} for i in xrange(64)]
attack90 = [{} for i in xrange(64)]
attack135 = [{} for i in xrange(64)]

cmap = [ 128, 64, 32, 16, 8, 4, 2, 1 ]
rot1 = [ A1, A2, A3, A4, A5, A6, A7, A8 ]
rot2 = [ A1, B2, C3, D4, E5, F6, G7, H8 ]
rot3 = [ A8, B7, C6, D5, E4, F3, G2, H1 ]

# To save time, we init a main line for each of the four directions, and next
# we will translate it for each possible cord
for cord in xrange(8):
    for map in xrange(1, 256):
        
        # Skip entries without cord set, as cord will always be set
        if not map & cmap[cord]:
            continue
        
        # Find limits inclusive
        cord1 = cord2 = cord
        while cord1 > 0:
            cord1 -= 1
            if cmap[cord1] & map: break
        while cord2 < 7:
            cord2 += 1
            if cmap[cord2] & map: break
        
        # Remember A1 is the left most bit
        map00 = createBoard(map << 56)
        
        attack00[cord][map00] = \
                fromToRay[cord][cord1] | \
                fromToRay[cord][cord2]
        
        map90 = createBoard(reduce(or_, (1 << 63-rot1[c] for c in iterBits(map00))))
        attack90[rot1[cord]][map90] = \
                fromToRay[rot1[cord]][rot1[cord1]] | \
                fromToRay[rot1[cord]][rot1[cord2]]
        
        map45 = createBoard(reduce(or_, (1 << 63-rot2[c] for c in iterBits(map00))))
        attack45[rot2[cord]][map45] = \
                fromToRay[rot2[cord]][rot2[cord1]] | \
                fromToRay[rot2[cord]][rot2[cord2]]
        
        map135 = createBoard(reduce(or_, (1 << 63-rot3[c] for c in iterBits(map00))))
        attack135[rot3[cord]][map135] = \
                fromToRay[rot3[cord]][rot3[cord1]] | \
                fromToRay[rot3[cord]][rot3[cord2]]


MAXBITBOARD = (1<<64)-1

for r in xrange(A2,A8+1,8):
	for cord in iterBits(ray00[r]):
		attack00[cord] = dict((map >> 8, ray >> 8)
                              for map,ray in attack00[cord-8].iteritems())

for r in xrange(B1,H1+1):
	for cord in iterBits(ray90[r]):
		attack90[cord] = dict((map >> 1, ray >> 1)
                              for map,ray in attack90[cord-1].iteritems())

# Bottom right
for r in xrange(B1,H1+1):
    for cord in iterBits(ray45[r]):
        attack45[cord] = dict((map << 8 & MAXBITBOARD, ray << 8 & MAXBITBOARD)
                              for map,ray in attack45[cord+8].iteritems())

# Top left
for r in reversed(xrange(A8,H8)):
    for cord in iterBits(ray45[r]):
        attack45[cord] = dict((map >> 8, ray >> 8)
                              for map,ray in attack45[cord-8].iteritems())

# Top right
for r in xrange(B8,H8+1):
    for cord in iterBits(ray135[r]):
        attack135[cord] = dict((map >> 8, ray >> 8)
                               for map,ray in attack135[cord-8].iteritems())

# Bottom left
for r in reversed(xrange(A1,H1)):
    for cord in iterBits(ray135[r]):
        attack135[cord] = dict((map << 8 & MAXBITBOARD, ray << 8 & MAXBITBOARD)
                               for map,ray in attack135[cord+8].iteritems())
