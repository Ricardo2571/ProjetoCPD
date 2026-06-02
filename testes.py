"""
Suite de Testes Unitários - Validação de Conformidade
Permite validação automática do código através da linha de comandos.
"""

import unittest

from game_of_life import game_of_life_parallel, game_of_life_sequential
from primos import find_max_prime_parallel, find_max_prime_sequential, is_prime


class TestPrimes(unittest.TestCase):
    """Bateria de testes focada na matemática primária e timing."""

    def test_is_prime_small(self) -> None:
        """Testa o comportamento da verificação de primos com algarismos básicos e de edge-cases."""
        for p in [2, 3, 5, 7, 11]: self.assertTrue(is_prime(p))
        for n in [0, 1, 4, 6, 8]: self.assertFalse(is_prime(n))

    def test_sequential_finds_prime(self) -> None:
        """Garante que a pesquisa de processo único encontra logicamente um número primo."""
        result, _ = find_max_prime_sequential(1)
        self.assertGreater(result, 1)
        self.assertTrue(is_prime(result))

    def test_parallel_finds_prime(self) -> None:
        """Garante que a coordenação paralela não perde consistência na extração do máximo."""
        result, _ = find_max_prime_parallel(1, 2)
        self.assertGreater(result, 1)
        self.assertTrue(is_prime(result))


class TestGameOfLife(unittest.TestCase):
    """Bateria de testes que utiliza padrões conhecidos do Autómato."""

    def test_blinker(self) -> None:
        """Testa o padrão oscilatório 'Blinker' base do Conway's Game of Life."""
        grid = [[0,0,0,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,0,0,0]]
        expected = [[0,0,0,0,0], [0,0,0,0,0], [0,1,1,1,0], [0,0,0,0,0], [0,0,0,0,0]]
        res = game_of_life_sequential(grid, 1)
        self.assertEqual(res, expected)

    def test_block_stable(self) -> None:
        """Testa um padrão estável estático ('Block') onde nenhuma vida avança ou regride."""
        grid = [[0,0,0,0], [0,1,1,0], [0,1,1,0], [0,0,0,0]]
        res = game_of_life_sequential(grid, 1)
        self.assertEqual(res, grid)

    def test_parallel_matches_sequential(self) -> None:
        """Confirma que o output sequencial bate de forma idempotente com o paralelizado e partilhado."""
        grid = [[0,0,0,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,1,0,0], [0,0,0,0,0]]
        seq = game_of_life_sequential(grid, 3)
        par = game_of_life_parallel(grid, 3, workers=2)
        self.assertEqual(seq, par)

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPrimes))
    suite.addTests(loader.loadTestsFromTestCase(TestGameOfLife))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)