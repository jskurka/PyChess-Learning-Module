#!/usr/bin/python

from pychess.Utils.const import *

features = {
    "setboard": 1,
    "analyze": 1,
    "usermove": 1,
    "reuse": 0,
    "draw": 1,
    "sigterm": 1,
    "myname": "PyChess %s" % VERSION
}

print "feature %s done=0" % \
            " ".join(["=".join([k,repr(v)]) for k,v in features.iteritems()])

################################################################################
# Import                                                                       #
################################################################################

from time import time
import sys, os
from threading import Lock

from pychess.System.ThreadPool import pool
import thread

from Engine import Engine
from pychess.Utils.book import getOpenings

from pychess.Utils.lutils.lsearch import alphaBeta
from pychess.Utils.lutils import lsearch
from pychess.Utils.lutils.lmove import toSAN, parseAny, parseSAN
from pychess.Utils.lutils.LBoard import LBoard, FEN_START

try:
    import psyco
    psyco.bind(alphaBeta)
except ImportError:
    pass

from pychess.Utils.const import prefix
import gettext
gettext.install("pychess", localedir=prefix("lang"), unicode=1)
from cStringIO import StringIO

################################################################################
# getBestOpening                                                               #
################################################################################

import random
def getBestOpening (board):
    score = 0
    move = None
    for m, w, d, l in getOpenings(board):
        s = (w+d/3.0)*random.random()
        if not move or s > score:
            move = m
            score = s
    return move

################################################################################
# global variables                                                             #
################################################################################

searchLock = Lock()

sd = 4
moves = None
increment = None
mytime = None
#optime = None
forced = False
analyzing = False

board = LBoard()
board.applyFen(FEN_START)

################################################################################
# analyze()                                                                    #
################################################################################

def analyze ():
    """ Searches, and prints info from, the position as stated in the cecp
        protocol """
        
    lsearch.searching = True
    start = time()
    searchLock.acquire()
    
    for depth in range (1, 10):
        if not lsearch.searching: break
        t = time()
        mvs, scr = alphaBeta (board, depth)
        
        smvs = []
        
        for move in mvs:
            smvs.append(toSAN (board, move))
            board.applyMove(move)
        for move in mvs:
            board.popMove()
            
        smvs = " ".join(smvs)
        
        print depth, "\t", "%0.2f" % (time()-start), "\t", scr, "\t", \
              lsearch.nodes, "\t", smvs
              
        print "%0.1f moves/position; %0.1f n/s" % \
               (lsearch.nodes/float(lsearch.movesearches), lsearch.nodes/(time()-t))
               
        lsearch.nodes = 0
        lsearch.movesearches = 0
        
    searchLock.release()

################################################################################
# analyze()                                                                    #
################################################################################

def go ():
    """ Finds and prints the best move from the current position """
    
    searchLock.acquire()
    
    # TODO: Length info should be put in the book.
    # Btw. 10 is not enough. Try 20
    if len(board.history) < 14:
        movestr = getBestOpening(board)
        if movestr:
            move = parseSAN(board, movestr)
        
    if len(board.history) >= 14 or not movestr:

        global mytime, increment
        lsearch.searching = True
        
        if mytime == None:
            mvs, scr = alphaBeta (board, sd)
            move = mvs[0]
        
        else:
            # We bet that the game will be about 30 moves. That gives us
            # starttime / 30 seconds per turn + the incremnt.
            # TODO: Create more sophisticated method.
            usetime = float(mytime) / max((30-len(history)),3)
            usetime = max (usetime, 5) # We don't wan't to search for e.g. 0 secs
            starttime = time()
            endtime = starttime + usetime
            print "Time left: %d seconds; Thinking for %d seconds" % \
                   (mytime, usetime)
            for depth in range(1,sd+1):
                mvs, scr = alphaBeta (board, depth)
                if time() > endtime: break
            move = mvs[0]
            mytime -= time() - starttime
            mytime += increment
        
        print "moves were", mvs
        
        lsearch.movesearches = 0
        lsearch.nodes = 0
        lsearch.searching = False
        
    print "move", toSAN(board, move)
    board.applyMove(move)
    
    searchLock.release()

while True:
    line = raw_input()
    if not line.strip(): continue
    lines = line.split()
    
    if lines[0] == "protover":
        print "features done=1"
    
    elif lines[0] == "usermove":
        
        lsearch.searching = False
        searchLock.acquire()
        searchLock.release()
        
        move = parseAny (board, lines[1])
        board.applyMove(move)
                
        if not forced and not analyzing:
            thread.start_new(go, ())
        
        if analyzing:
            thread.start_new(analyze, ())
        
    elif lines[0] == "sd":
        sd = int(lines[1])
        if sd < 4: sd = 1
        if 4 <= sd <= 7: sd = 2
        if 7 < sd: sd = 3
        
    elif lines[0] == "level":
        moves = int(lines[1])
        increment = int(lines[3])
        minutes = lines[2].split(":")
        mytime = int(minutes[0])*60
        if len(minutes) > 1:
            mytime += int(minutes[1])
        print "Playing %d moves in %d seconds + %d increment" % (moves, mytime, increment)
    
    elif lines[0] == "time":
        mytime = int(lines[1])
    
    #elif lines[0] == "otim":
    #   optime = int(lines[1])
    
    elif lines[0] == "quit":
        sys.exit()
    
    elif lines[0] == "force":
        forced = True
    
    elif lines[0] == "go":
        forced = False
        thread.start_new(go, ())
    
    elif lines[0] in ("black", "white"):
        lsearch.searching = False
        searchLock.acquire()
        newColor = lines[0] == "black" and BLACK or WHITE
        if board.color != newColor:
            board.setColor(newColor)
        searchLock.release()
        if analyzing:
            thread.start_new(analyze, ())
    
    elif lines[0] == "analyze":
        analyzing = True
        thread.start_new(analyze, ())
        
    elif lines[0] == "draw":
        print "offer draw"
    
    elif lines[0] == "setboard":
        lsearch.searching = False
        io = StringIO()
        io.write(" ".join(lines[1:])+"\n")
        io.seek(0)
        epdfile = epd.load(io)
        io.close()
        searchLock.acquire()
        history = epdfile.loadToHistory(0,-1)
        searchLock.release()
        if analyzing:
            thread.start_new(analyze, ())
    
    elif lines[0] in ("xboard", "otim", "hard", "easy" "nopost", "post"):
        pass
    
    else: print "Error (unknown command):", line
