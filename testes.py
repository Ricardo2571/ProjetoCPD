"""
Suite de Testes Unitários Otimizada
Permite validação automática do código através da linha de comandos.
"""

import unittest
from primos import is_prime, find_max_prime_sequential, find_max_prime_parallel
from game_of_life import game_of_life_sequential, game_of_life_parallel

class TestPrimes(unittest.TestCase):

    def test_is_prime_small(self):
        """Valida que a função obrigatória retorna verdade para primos e falso para não-primos."""
        for p in [2, 3, 5, 7, 11]:
            self.assertTrue(is_prime(p))
        for n in [0, 1, 4, 6, 8]:
            self.assertFalse(is_prime(n))

    def test_sequential_finds_prime(self):
        """Valida a execução e término atempado da abordagem sequencial (timeout: 1s)."""
        result = find_max_prime_sequential(1)
        self.assertGreater(result, 1)
        self.assertTrue(is_prime(result))

    def test_parallel_finds_prime(self):
        """Valida a execução paralela, término síncrono e integridade do resultado em MP."""
        result = find_max_prime_parallel(1, 2)
        self.assertGreater(result, 1)
        self.assertTrue(is_prime(result))


class TestGameOfLife(unittest.TestCase):

    def test_blinker_oscillator(self):
        """
        Validação Algorítmica (Regras de Conway):
        Testa o padrão Blinker, onde uma barra vertical se torna horizontal ao fim de 1 geração.
        """
        grid = [
            [0,0,0,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,0,0,0]
        ]
        expected = [
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,1,1,1,0],
            [0,0,0,0,0],
            [0,0,0,0,0]
        ]
        res = game_of_life_sequential(grid, 1)
        self.assertEqual(res, expected)

    def test_block_stable(self):
        """Testa um padrão estável (Block) que não se deve alterar com a passagem do tempo."""
        grid = [
            [0,0,0,0],
            [0,1,1,0],
            [0,1,1,0],
            [0,0,0,0]
        ]
        res = game_of_life_sequential(grid, 1)
        self.assertEqual(res, grid)

    def test_parallel_matches_sequential(self):
        """
        Testa explicitamente o Requisito 3.2.1:
        'Consistência dos resultados (Paralelo) face à versão sequencial'.
        """
        grid = [
            [0,0,0,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,0,0,0]
        ]
        # Evoluímos ambas as lógicas durante 3 gerações
        seq = game_of_life_sequential(grid, 3)
        par = game_of_life_parallel(grid, 3, workers=2)

        self.assertEqual(seq, par)

if __name__ == '__main__':
    # Estrutura standard para permitir a auto-validação de linha de comandos
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPrimes))
    suite.addTests(loader.loadTestsFromTestCase(TestGameOfLife))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)