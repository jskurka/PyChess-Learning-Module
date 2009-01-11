from time import time
from random import random
from heapq import heappush, heappop

from lmovegen import genAllMoves, genCheckEvasions, genCaptures
from pychess.Utils.const import *
from leval import evaluateComplete
from lsort import getCaptureValue, getMoveValue
from lmove import toSAN
from ldata import MATE_VALUE
from TranspositionTable import TranspositionTable
import ldraw
from pychess.Utils.lutils.egtb_k4it import probeEndGameTable

TIMECHECK_FREQ = 500

table = TranspositionTable(5000000)
skipPruneChance = 0
searching = False
movesearches = 0
nodes = 0
last = 0
endtime = 0
timecheck_counter = TIMECHECK_FREQ
useegtb = False

def alphaBeta (board, depth, alpha=-MATE_VALUE, beta=MATE_VALUE, ply=0):
    """ This is a alphabeta/negamax/quiescent/iterativedeepend search algorithm
        Based on moves found by the validator.py findmoves2 function and
        evaluated by eval.py.
        
        The function recalls itself "depth" times. If the last move in range
        depth was a capture, it will continue calling itself, only searching for
        captures.
        
        It returns a tuple of
        *   a list of the path it found through the search tree (last item being
            the deepest)
        *   a score of your standing the the last possition. """
    
    global last, searching, nodes, movesearches, table, endtime, timecheck_counter
    foundPv = False
    hashf = hashfALPHA
    amove = []
    
    ############################################################################
    # Look in the end game table
    ############################################################################
    
    if useegtb:
        egtb = probeEndGameTable(board)
        if egtb:
            move, state, steps = egtb[0]
            
            if state == DRAW:
                score = 0
            elif board.color == WHITE:
                if state == WHITEWON:
                    score = MATE_VALUE-steps+2
                else: score = -MATE_VALUE+steps-2
            else:
                if state == WHITEWON:
                    score = -MATE_VALUE+steps-2
                else: score = MATE_VALUE-steps+2
            last = 1
            return [move], score
    
    ###########################################################################
    # We don't save repetition in the table, so we need to test draw before   #
    # table.                                                                  #
    ###########################################################################
    
    # We don't adjudicate draws. Clients may have different rules for that.
    if ply > 0:
    	if ldraw.test(board):
        	last = 2
	        return [], 0
    
    ############################################################################
    # Look up transposition table                                              #
    ############################################################################
    
    table.setHashMove (depth, -1)
    probe = table.probe (board, depth, alpha, beta)
    hashmove = None
    if probe:
        move, score, hashf = probe
        hashmove = move
        table.setHashMove (depth, move)
        
        if hashf == hashfEXACT:
            last = 3
            return [move], score
        elif hashf == hashfBETA:
            beta = min(score, beta)
        elif hashf == hashfALPHA:
            alpha = score
            
        if hashf != hashfBAD and alpha >= beta:
            last = 4
            return [move], score
    
    ############################################################################
    # Cheking the time                                                         #
    ############################################################################

    timecheck_counter -= 1
    if timecheck_counter == 0:
        if time() > endtime:
            searching = False
        timecheck_counter = TIMECHECK_FREQ
    
    ############################################################################
    # Break itereation if interupted or if times up                            #
    ############################################################################
    
    if not searching:
        last = 5
        return [], -evaluateComplete(board, 1-board.color)
    
    ############################################################################
    # Go for quiescent search                                                  #
    ############################################################################
    
    isCheck = board.isChecked()
    
    if depth <= 0:
        if isCheck:
            # Being in check is that serious, that we want to take a deeper look
            depth += 1
        else:
            last = 6
            mvs, val = quiescent(board, alpha, beta, ply)
            return mvs, val
    
    ############################################################################
    # Find and sort moves                                                      #
    ############################################################################
    
    movesearches += 1
    
    if isCheck:
        moves = [(-getMoveValue(board,table,depth,m),m) for m in genCheckEvasions(board)]
    else: moves = [(-getMoveValue(board,table,depth,m),m) for m in genAllMoves(board)]
    moves.sort()
    
    # This is needed on checkmate
    catchFailLow = None
    
    ############################################################################
    # Loop moves                                                               #
    ############################################################################
    
    
    for moveValue, move in moves:
        
        nodes += 1
        
        board.applyMove(move)
        if not isCheck:
            if board.opIsChecked():
                board.popMove()
                continue
        
        catchFailLow = move
        
        if foundPv:
            mvs, val = alphaBeta (board, depth-1, -alpha-1, -alpha, ply+1)
            val = -val
            if val > alpha and val < beta:
                mvs, val = alphaBeta (board, depth-1, -beta, -alpha, ply+1)
                val = -val
        else:
            mvs, val = alphaBeta (board, depth-1, -beta, -alpha, ply+1)
            val = -val
        
        board.popMove()
        
        if val > alpha:
            if val >= beta:
                if searching:
                    table.record (board, move, beta, hashfBETA, depth)
                    # We don't want to use our valuable killer move spaces for
                    # captures and promotions, as these are searched early anyways.
                    if board.arBoard[move&63] == EMPTY and \
                            not move>>12 in PROMOTIONS:
                        table.addKiller (depth, move)
                        table.addButterfly(move, depth)
                last = 7
                return [move]+mvs, beta
            
            alpha = val
            amove = [move]+mvs
            hashf = hashfEXACT
            foundPv = True
    
    ############################################################################
    # Return                                                                   #
    ############################################################################
    
    if amove:
        if searching:
            table.record (board, amove[0], alpha, hashf, depth)
            if board.arBoard[amove[0]&63] == EMPTY:
                table.addKiller (depth, amove[0])
        last = 8
        return amove, alpha
    
    if catchFailLow:
        if searching:
            table.record (board, catchFailLow, alpha, hashf, depth)
        last = 9
        return [catchFailLow], alpha

    # If no moves were found, this must be a mate or stalemate
    if isCheck:
        last = 10
        return [], -MATE_VALUE+ply-2
    
    last = 11
    return [], 0

def quiescent (board, alpha, beta, ply):
    
    if skipPruneChance and random() < skipPruneChance:
        return [], (alpha+beta)/2
    
    global nodes
    
    if ldraw.test(board):
        return [], 0
    
    isCheck = board.isChecked()
    
    # Our quiescent search will evaluate the current board, and if 
    value = evaluateComplete(board, board.color)
    if value >= beta and not isCheck:
        return [], beta
    if value > alpha:
        alpha = value
    
    amove = []
    
    heap = []
    
    if isCheck:
        someMove = False
        for move in genCheckEvasions(board):
            someMove = True
            # Heap.append is fine, as we don't really do sorting on the few moves
            heap.append((0, move))
        if not someMove:
            return [], -MATE_VALUE+ply-2
    else:
        for move in genCaptures (board):
            heappush(heap, (-getCaptureValue (board, move), move))
    
    while heap:
        
        nodes += 1
        
        v, move = heappop(heap)
        
        board.applyMove(move)
        if board.opIsChecked():
            board.popMove()
            continue
        
        mvs, val = quiescent(board, -beta, -alpha, ply+1)
        val = -val
        
        board.popMove()
        
        if val >= beta:
            return [move]+mvs, beta
        
        if val > alpha:
            alpha = val
            amove = [move]+mvs
    
    if amove:
        return amove, alpha
    
    else:
        return [], alpha
