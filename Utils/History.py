#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from time import time

import pygtk
pygtk.require("2.0")
import gtk

WHITE_OO = 1
WHITE_OOO = 2
BLACK_OO = 4
BLACK_OOO = 8

class HistoryPool:
    def __init__ (self):
        self.objects = []
    def pop (self):
        if len(self.objects) <= 0:
            self.objects.append(History())
        return self.objects.pop()
    def add (self, history):
        #Todo: deconnect signals
        self.objects.append(history)
hisPool = HistoryPool()

from Piece import Piece
def c (str):
    color = str[0] == "w" and "white" or "black"
    return Piece (color, str[1])

from Board import Board
startBoard = Board(
[[c("wr"),c("wn"),c("wb"),c("wq"),c("wk"),c("wb"),c("wn"),c("wr")],
[c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp")],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp")],
[c("br"),c("bn"),c("bb"),c("bq"),c("bk"),c("bb"),c("bn"),c("br")]])

from Utils.Move import Move
from System.Log import log
import validator

from copy import copy
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

def cloneStartPieces ():
    l = []
    for row in startPieces:
        l.append([])
        for piece in row:
            l[-1].append(piece)
    return l

def rm (var, opp):
    if var & opp:
        return var ^ opp
    return var

class History (GObject):
    '''Class remembers all moves, and can give you
    a two dimensional array (8x8) of Piece objects'''
    
    __gsignals__ = {
        'changed': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'cleared': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'game_ended' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,))
    }
    
    def __init__ (self, mvlist=False):
        GObject.__init__(self)
        self.reset(mvlist)
    
    def reset (self, mvlist=False):
        GObject.__init__(self)
        
        self.boards = [startBoard.clone()]
        self.fifty = 0
        self.moves = []
        self.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        self.movelist = []
        if mvlist:
            self.movelist.append(validator.findMoves(self))
        
        self.emit("cleared")
    
    def __getitem__(self, i):
        return self.boards[i]
    
    def __len__(self):
        return len(self.boards)
    
    def curCol (self):
        return len(self) % 2 == 1 and "white" or "black"
    
    def add (self, move, mvlist=False):
    
        capture = self.boards[-1][move.cord1] != None
        
        if move.castling:
            c = str(move.castling[0])
            if c == 'a1': self.castling = rm(self.castling, WHITE_OOO)
            elif c == 'h1': self.castling = rm(self.castling, WHITE_OO)
            elif c == 'a8': self.castling = rm(self.castling, BLACK_OOO)
            elif c == 'h8': self.castling = rm(self.castling, BLACK_OO)

        p = self.boards[-1][move.cord0]

        if p.sign == "k":
            if p.color == "black":
                self.castling = rm(self.castling, BLACK_OO)
                self.castling = rm(self.castling, BLACK_OOO)
            elif p.color == "white":
                self.castling = rm(self.castling, WHITE_OO)
                self.castling = rm(self.castling, WHITE_OOO)
        
        elif p.sign == "r":
            c = str(move.cord0)
            if c == 'a1': self.castling = rm(self.castling, WHITE_OOO)
            elif c == 'h1': self.castling = rm(self.castling, WHITE_OO)
            elif c == 'a8': self.castling = rm(self.castling, BLACK_OOO)
            elif c == 'h8': self.castling = rm(self.castling, BLACK_OO)
        
        self.moves.append(move)
        self.boards.append(self.boards[-1].move(move))

        if capture or self.boards[-1][move.cord1].sign != "p":
            self.fifty += 1
        else: self.fifty = 0
        
        # Emiting before the add is really completed
        #    (hasn't yet generated movelist) for better performace
        self.emit("changed")
        
        if mvlist:
            self.movelist.append(validator.findMoves(self))
        
        if len(self.movelist) > 0:
            s = validator.status(self)
            if s == validator.STALE:
                self.locked = True
                self.emit("game_ended", s)
                return False
            elif s == validator.MATE:
                self.locked = True
                self.emit("game_ended", s)
                return False
        
        return self
    
    def clone (self):
        his = hisPool.pop()
        his.castling = self.castling
        his.fifty = self.fifty
        his.moves = copy(self.moves)
        his.boards = copy(self.boards)
        return his
