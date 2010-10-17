import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

modules_to_test = (
    "bitboard",
    "draw",
    "eval",
    "fen",
    "frc_castling",
    "frc_movegen",
    "move",
    "movegen",
    "pgn",
    "zobrist",
    'ficsmanagers',
    'analysis',
    ) 

def suite():
    tests = unittest.TestSuite()
    for module in map(__import__, modules_to_test):
        tests.addTest(unittest.findTestCases(module))
    return tests

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

