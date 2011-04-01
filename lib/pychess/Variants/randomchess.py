# Random Chess

import random

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class RandomBoard(Board):
    variant = RANDOMCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=self.random_start())
        else:
            Board.__init__(self, setup=setup)

    def random_start(self):        
        tmp = random.sample(('r', 'n', 'b', 'q')*16, 7)
        tmp.append('k')
        random.shuffle(tmp)
        tmp = ''.join(tmp)
        tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w - - 0 1'
        
        return tmp


class RandomChess:
    __desc__ = _("FICS wild/3: http://www.freechess.org/Help/HelpFiles/wild.html\n" +
                 "* Randomly chosen pieces (two queens or three rooks possible)\n" +
                 "* Exactly one king of each color\n" +
                 "* Pieces placed randomly behind the pawns\n" +
                 "* No castling\n" +
                 "* Black's arrangement mirrors white's")
    name = _("Random")
    cecp_name = "unknown"
    board = RandomBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_SHUFFLE


if __name__ == '__main__':
    Board = RandomBoard(True)
    for i in range(10):
        print Board.random_start()
