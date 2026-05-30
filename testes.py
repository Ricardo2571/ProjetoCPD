"""Optimized test suite - all tests in minimal code."""

import unittest
import time
from primos import is_prime, find_max_prime_sequential, find_max_prime_parallel
from game_of_life import game_of_life_sequential, game_of_life_parallel, count_neighbors, get_next_generation


class TestPrimes(unittest.TestCase):
    def test_is_prime_small(self):
        for p in [2, 3, 5, 7, 11]: self.assertTrue(is_prime(p))
        for n in [0, 1, 4, 6, 8]: self.assertFalse(is_prime(n))

    def test_sequential_finds_prime(self):
        result = find_max_prime_sequential(1)
        self.assertGreater(result, 1)
        self.assertTrue(is_prime(result))

    def test_parallel_finds_prime(self):
        result = find_max_prime_parallel(1, 2)
        self.assertGreater(result, 1)
        self.assertTrue(is_prime(result))


class TestGameOfLife(unittest.TestCase):
    def test_count_neighbors(self):
        grid = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
        self.assertEqual(count_neighbors(grid, 1, 1), 8)

    def test_blinker(self):
        grid = [[0,0,0,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,0,0,0]]
        next_gen = get_next_generation(grid)
        expected = [[0,0,0,0,0], [0,0,0,0,0], [0,1,1,1,0], [0,0,0,0,0], [0,0,0,0,0]]
        self.assertEqual(next_gen, expected)

    def test_block_stable(self):
        grid = [[0,0,0,0], [0,1,1,0], [0,1,1,0], [0,0,0,0]]
        next_gen = get_next_generation(grid)
        self.assertEqual(next_gen, grid)

    def test_sequential(self):
        grid = [[0,0,0,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,0,0,0]]
        result = game_of_life_sequential(grid, 5)
        self.assertEqual(len(result), 5)
        self.assertEqual(len(result[0]), 5)

    def test_parallel_matches_sequential(self):
        grid = [[0,0,0,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,0,0,0]]
        seq = game_of_life_sequential(grid, 3)
        par = game_of_life_parallel(grid, 3, 2)
        self.assertEqual(seq, par)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPrimes))
    suite.addTests(loader.loadTestsFromTestCase(TestGameOfLife))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
