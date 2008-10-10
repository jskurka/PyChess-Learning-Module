import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import *
from pychess.Utils.lutils.leval import LBoard
from pychess.Utils.lutils.lmove import newMove
from pychess.Variants.fischerandom import frc_castling_moves

data = (
 ("r3k2r/8/8/8/8/8/8/R3K2R w AH - 0 1", [(E1, G1, KING_CASTLE), (E1, C1, QUEEN_CASTLE)]),
 ("r3k2r/8/8/8/8/8/8/R3K2R b ah - 0 1", [(E8, G8, KING_CASTLE), (E8, C8, QUEEN_CASTLE)]),
 ("2r1k2r/8/8/8/8/8/8/2R1K2R w H - 0 1", [(E1, G1, KING_CASTLE)]),
 ("2r1k2r/8/8/8/8/8/8/2R1K2R b h - 0 1", [(E8, G8, KING_CASTLE)]),
 ("3rk1qr/8/8/8/8/8/8/3RK1QR w - - 0 1", []),
 ("3rk1qr/8/8/8/8/8/8/3RK1QR b - - 0 1", []),
 )

class FRCCastlingTestCase(unittest.TestCase):

    def testFRCCastling(self):
        """Testing FRC castling movegen"""
        print

        board = LBoard(FISCHERRANDOMCHESS)

        for fen, castles in data:
            print fen
            board.applyFen(fen)
            #print board
            moves = [move for move in frc_castling_moves(board)]
            self.assertEqual(len(moves), len(castles))
            for i, castle in enumerate(castles):
                kfrom, kto, flag = castle
                self.assertEqual(moves[i], newMove(kfrom, kto, flag))


if __name__ == '__main__':
    unittest.main()
