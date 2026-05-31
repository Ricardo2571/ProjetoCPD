"""
Módulo Game of Life
Implementa o autómato celular de John Conway com abordagens sequencial e paralela.
"""

import multiprocessing as mp
import ctypes

def _count_neighbors(grid_1d, r: int, c: int, rows: int, cols: int) -> int:
    """
    Conta o número de vizinhos vivos (1) de uma célula na grelha 1D.
    Assegura que as fronteiras não são ultrapassadas (fronteira NÃO cíclica,
    como estritamente definido no enunciado).
    """
    count = 0
    # Limites estritos para garantir o respeito pelas fronteiras físicas da grelha
    r_start = max(0, r - 1)
    r_end = min(rows, r + 2)
    c_start = max(0, c - 1)
    c_end = min(cols, c + 2)

    for i in range(r_start, r_end):
        row_offset = i * cols
        for j in range(c_start, c_end):
            # Ignora a própria célula central
            if i == r and j == c:
                continue
            if grid_1d[row_offset + j] == 1:
                count += 1
    return count

def game_of_life_sequential(grid: list, generations: int) -> list:
    """
    Simula a evolução da grelha de forma sequencial.

    :param grid: Matriz 2D inicial (lista de listas) com 0s e 1s.
    :param generations: Número de iterações/gerações a simular.
    :return: Matriz 2D final após as gerações especificadas.
    """
    if not grid or not grid[0]:
        return grid

    rows = len(grid)
    cols = len(grid[0])

    # Transformação de matriz 2D numa lista 1D para maximizar a localidade em cache e velocidade
    current_grid = [val for row in grid for val in row]

    for _ in range(generations):
        next_grid = [0] * (rows * cols)

        for r in range(rows):
            row_offset = r * cols
            for c in range(cols):
                idx = row_offset + c
                live_neighbors = _count_neighbors(current_grid, r, c, rows, cols)

                # Aplicação rigorosa das 4 Regras de Conway
                if current_grid[idx] == 1:
                    # Sobrevive
                    if live_neighbors == 2 or live_neighbors == 3:
                        next_grid[idx] = 1
                else:
                    # Nasce
                    if live_neighbors == 3:
                        next_grid[idx] = 1

        current_grid = next_grid

    # Reconstrói e devolve a matriz no formato original 2D
    final_grid = []
    for r in range(rows):
        start_idx = r * cols
        final_grid.append(current_grid[start_idx: start_idx + cols])

    return final_grid

def _worker_gol(worker_id: int, num_workers: int, rows: int, cols: int,
                arr_a, arr_b, generations: int, barrier):
    """
    Estratégia de divisão de trabalho e sincronização:
    Cada worker é responsável exclusivamente por um subconjunto de LINHAS da grelha.
    A barreira garante sincronização consistente no final de cada geração.
    """
    # 1. DIVISÃO HORIZONTAL (Gestão de Concorrência sem Locks)
    # Como as linhas processadas são estritamente separadas, garantimos a
    # ausência total de "Race Conditions" na escrita.
    chunk = rows // num_workers
    start_row = worker_id * chunk
    # O último worker absorve as linhas extra em caso de divisão não exata
    end_row = rows if worker_id == num_workers - 1 else (worker_id + 1) * chunk

    for gen in range(generations):
        # Double-Buffering (Ping-Pong): Uma grelha é apenas leitura, a outra apenas escrita.
        # Alternam a cada geração para atualizar os resultados consistentemente.
        if gen % 2 == 0:
            read_arr, write_arr = arr_a, arr_b
        else:
            read_arr, write_arr = arr_b, arr_a

        for r in range(start_row, end_row):
            row_offset = r * cols
            for c in range(cols):
                idx = row_offset + c

                live_neighbors = _count_neighbors(read_arr, r, c, rows, cols)

                current_state = read_arr[idx]
                if current_state == 1:
                    if live_neighbors == 2 or live_neighbors == 3:
                        write_arr[idx] = 1
                    else:
                        write_arr[idx] = 0
                else:
                    if live_neighbors == 3:
                        write_arr[idx] = 1
                    else:
                        write_arr[idx] = 0

        # 2. COORDENAÇÃO E SINCRONIZAÇÃO ENTRE GERAÇÕES
        # Nenhum worker pode avançar para a geração n+1 sem que todos terminem a geração n
        barrier.wait()

def game_of_life_parallel(grid: list, generations: int, workers: int) -> list:
    """
    Simula a evolução da grelha recorrendo a múltiplos processos trabalhadores.
    """
    if not grid or not grid[0]:
        return grid

    rows = len(grid)
    cols = len(grid[0])

    # Se pedirem mais workers do que linhas, rebaixamos automaticamente
    # para evitar sobrecarga (overhead) sem benefício associado.
    workers = min(workers, rows)

    if workers <= 1:
        return game_of_life_sequential(grid, generations)

    # Memórias partilhadas nativas (C-Types)
    # Utilizadas em vez de Queues ou Pipes para transferência de matrizes grandes
    # porque anulam o pesado tempo de "pickling" (serialização) do Python.
    arr_a = mp.RawArray(ctypes.c_byte, rows * cols)
    arr_b = mp.RawArray(ctypes.c_byte, rows * cols)

    for r in range(rows):
        for c in range(cols):
            arr_a[r * cols + c] = grid[r][c]

    # Barreira de bloqueio para Múltiplos Workers
    barrier = mp.Barrier(workers)
    processos = []

    for i in range(workers):
        p = mp.Process(
            target=_worker_gol,
            args=(i, workers, rows, cols, arr_a, arr_b, generations, barrier)
        )
        p.start()
        processos.append(p)

    # Terminação coordenada de todos os workers (join estrito)
    for p in processos:
        p.join()

    # Identificar a matriz com o último estado válido
    final_arr = arr_a if generations % 2 == 0 else arr_b

    final_grid = []
    for r in range(rows):
        start_idx = r * cols
        final_grid.append(list(final_arr[start_idx: start_idx + cols]))

    return final_grid