from pychess.Utils.History import History
from pychess.Utils.Move import *
from pychess.Utils.const import *
from pychess.System.Log import log
import datetime

__label__ = _("Chess Game")
__endings__ = "pgn",

def save (file, game):
    history = game.history

    #from pwd import getpwuid
    #from os import getuid
    #userdata = getpwuid(getuid())
    #name = userdata.pw_gecos
    #if not name:
    #    name = userdata.pw_name
    
    #result = reprResult[history.status]
    game_status = reprResult[game.history.boards[-1].status]

    print >> file, '[Event "%s"]' % game.event 
    print >> file, '[Site "%s"]' % game.site
    print >> file, '[Date "%04d.%02d.%02d"]' % (game.year, game.month, game.day)
    print >> file, '[Round "%d"]' % game.round
    print >> file, '[White "White Player"]'
    print >> file, '[Black "Black Player"]'
    print >> file, '[Result "%s"]' % game_status
    print >> file

    halfMoves = 0
    temphis = History()
    result = ''
    for move in history.moves:
        if halfMoves % 2 == 0:
            result += str((halfMoves / 2) + 1)
            result += '. '
        temphis.add(move)
        result += toSAN(temphis[-2], temphis[-1], temphis.moves[-1])
        result += ' '
        if len(result) >= 80:
            result += '\n'
            file.write(result)
            result = ''
        halfMoves += 1
    result += game_status + '\n'
    file.write(result)
    file.close()

def stripBrackets (string):
    brackets = 0
    end = 0
    result = ""
    for i, c in enumerate(string):
        if c == '(':
            if brackets == 0:
                result += string[end:i]
            brackets += 1
        elif c == ')':
            brackets -= 1
            if brackets == 0:
                end = i+1
    result += string[end:]
    return result

import re
tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+\"(.+?)\"\]")
movre = re.compile(r"([a-hxOoKQRBN0-8+#=-]{2,7})\s")
comre = re.compile(r"(?:\{.*?\})|(?:;.*?[\n\r])|(?:\$[0-9]+)", re.DOTALL)

def load (file):
    files = []
    inTags = False
    
    for line in file:
        line = line.lstrip()
        if not line: continue
        elif line.startswith("%"): continue
        
        if line.startswith("["):
            if not inTags:
                files.append(["",""])
                inTags = True
            files[-1][0] += line
        
        else:
            inTags = False
            files[-1][1] += line
    
    return PGNFile (files)

from ChessFile import ChessFile

class PGNFile (ChessFile):
    
    def __init__ (self, games):
        ChessFile.__init__(self, games)
        self.expect = None
        self.tagcache = {}
    
    def _parseMoves (self, gameno):
        moves = comre.sub("", self.games[gameno][1])
        moves = stripBrackets(moves)
        moves = movre.findall(moves+" ")
        if moves and moves[-1] in ("*", "1/2-1/2", "1-0", "0-1"):
            del moves[-1]
        return moves
    
    def loadToHistory2 (self, gameno, position, history=None):
        from profile import runctx
        loc = locals()
        loc["self"] = self
        runctx ("self.loadToHistory2(gameno, position, history)",
                loc, globals(), "/tmp/pychessprofile")
        from pstats import Stats
        s = Stats("/tmp/pychessprofile")
        s.sort_stats("time")
        s.print_stats()
        
    def loadToHistory (self, gameno, position, history=None):
        moves = self._parseMoves (gameno)
        if not history: history = History()
                
        for i, movestr in enumerate(moves):
            
            if position != -1 and i >= position: break
            
            m = self.parseMove (history[-1], movestr)
            if not m: continue
            
            if i+1 < len(moves) and (position == -1 or i+1 < position):
                history.add(m, False)
            else: history.add(m, True)
        
        assert history[-1].movelist
        
        return history
    
    def parseMove (self, board, movestr):
        if self.expect == None or self.expect == SAN:
            try: return parseSAN (board, movestr)
            except ParsingError:
                try:
                    self.expect = LAN
                    return parseLAN (board, movestr)
                except ParsingError:
                    try:
                        self.expect = AN
                        return parseAN (board, movestr)
                    except ParsingError:
                        return None
                        
        elif self.expect == LAN:
            try: return parseLAN (board, movestr)
            except ParsingError:
                try:
                    self.expect = SAN
                    return parseSAN (board, movestr)
                except ParsingError:
                    try:
                        self.expect = AN
                        return parseAN (board, movestr)
                    except ParsingError:
                        return None
                        
        elif self.expect == AN:
            try: return parseAN (board, movestr)
            except ParsingError:
                try:
                    self.expect = LAN
                    return parseLAN (board, movestr)
                except ParsingError:
                    try:
                        self.expect = SAN
                        return parseSAN (board, movestr)
                    except ParsingError:
                        return None
    
    def _getTag (self, gameno, tagkey):
        if gameno in self.tagcache:
            if tagkey in self.tagcache[gameno]:
                return self.tagcache[gameno][tagkey]
            else: return None
        else:
            self.tagcache[gameno] = dict(tagre.findall(self.games[gameno][0]))
            return self._getTag(gameno, tagkey)
    
    def get_player_names (self, no):
        p1 = self._getTag(no,"White") and self._getTag(no,"White") or "Unknown"
        p2 = self._getTag(no,"Black") and self._getTag(no,"Black") or "Unknown"
        return (p1, p2)
    
    def get_elo (self, no):
        p1 = self._getTag(no,"WhiteElo") and self._getTag(no,"WhiteElo") or "1600"
        p2 = self._getTag(no,"BlackElo") and self._getTag(no,"BlackElo") or "1600"
        p1 = p1.isdigit() and int(p1) or 1600
        p2 = p2.isdigit() and int(p2) or 1600
        return (p1, p2)
    
    def get_date (self, no):
        date = self._getTag(no,"Date")
        today = datetime.date.today()
        if not date:
            return today.timetuple()[:3]
        return [ s.isdigit() and int(s) or today.timetuple()[i] \
                 for i,s in enumerate(date.split(".")) ]
    
    def get_site (self, no):
        return self._getTag(no,"Site") and self._getTag(no,"Site") or "?"
    
    def get_event (self, no):
        return self._getTag(no,"Event") and self._getTag(no,"Event") or "?"
    
    def get_round (self, no):
        round = self._getTag(no,"Round")
        if not round: return 1
        if round.find(".") >= 1:
            round = round[:round.find(".")]
        if not round.isdigit(): return 1
        return int(round)
        
    def get_result (self, no):
        pgn2Const = {"*":RUNNING, "1/2-1/2":DRAW, "1-0":WHITEWON, "0-1":BLACKWON}
        if self._getTag(no,"Result") in pgn2Const:
            return pgn2Const[self._getTag(no,"Result")]
        return RUNNING
