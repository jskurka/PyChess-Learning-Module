# Shuffle Chess (nocastle variant in xboard terms)
# http://en.wikipedia.org/wiki/Chess960#Other_related_chess_variants

import random

from pychess.Utils.const import *
from pychess.Utils.Board import Board


class ShuffleBoard(Board):
    variant = SHUFFLECHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start())
        else:
            Board.__init__(self, setup=setup)

    def shuffle_start(self):
        """ Create a random initial position.
            No additional restrictions.
            Castling only possible when king and rook are
            on their traditional starting squares."""
        
        tmp = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        random.shuffle(tmp)
        
        if tmp[4] == 'k' and tmp[0] == 'r' and tmp[7] == 'r':
            castling = 'KQkq'
        elif tmp[4] == 'k' and tmp[0] == 'r':
            castling = 'Qq'
        elif tmp[4] == 'k' and tmp[7] == 'r':
            castling = 'Kk'
        else:
            castling = '-'

        tmp = ''.join(tmp)
        tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w ' + castling + ' - 0 1'
        
        return tmp


class ShuffleChess:
    name = _("No castle")
    cecp_name = "nocastle"
    board = ShuffleBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_SHUFFLE


if __name__ == '__main__':
    Board = ShuffleBoard(True)
    for i in range(10):
        print Board.shuffle_start()
