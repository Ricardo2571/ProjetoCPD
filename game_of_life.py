"""
Módulo Game of Life
Implementa o autómato celular de John Conway com abordagens sequencial e paralela.
"""

import multiprocessing as mp
import ctypes


def _count_neighbors(grid_1d, r: int, c: int, rows: int, cols: int) -> int:
    """
    Conta o número de vizinhos vivos (1) de uma célula na grelha 1D.
    Assegura que as fronteiras não são ultrapassadas (grelha não cíclica).
    """
    count = 0
    # Determina as fronteiras de verificação (garante que não sai da grelha)
    r_start = max(0, r - 1)
    r_end = min(rows, r + 2)
    c_start = max(0, c - 1)
    c_end = min(cols, c + 2)

    for i in range(r_start, r_end):
        row_offset = i * cols
        for j in range(c_start, c_end):
            # Ignora a própria célula
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

    # Achatamos a grelha para uma lista 1D por questões de simplicidade e velocidade
    current_grid = [val for row in grid for val in row]

    for _ in range(generations):
        next_grid = [0] * (rows * cols)

        for r in range(rows):
            row_offset = r * cols
            for c in range(cols):
                idx = row_offset + c
                live_neighbors = _count_neighbors(current_grid, r, c, rows, cols)

                # Regras do Game of Life
                if current_grid[idx] == 1:
                    if live_neighbors == 2 or live_neighbors == 3:
                        next_grid[idx] = 1
                else:
                    if live_neighbors == 3:
                        next_grid[idx] = 1

        current_grid = next_grid

    # Reconstrói a lista de listas 2D no final
    final_grid = []
    for r in range(rows):
        start_idx = r * cols
        final_grid.append(current_grid[start_idx: start_idx + cols])

    return final_grid


def _worker_gol(worker_id: int, num_workers: int, rows: int, cols: int,
                arr_a, arr_b, generations: int, barrier):
    """
    Worker que processa uma fatia específica da grelha em paralelo.
    Utiliza uma Barreira para garantir a sincronização temporal entre gerações.
    """
    # 1. DIVISÃO DO TRABALHO: Divisão horizontal (por linhas)
    # Cada worker calcula o seu bloco de linhas para evitar Race Conditions.
    chunk = rows // num_workers
    start_row = worker_id * chunk
    # O último worker assume o resto das linhas para garantir que nada fica para trás
    end_row = rows if worker_id == num_workers - 1 else (worker_id + 1) * chunk

    for gen in range(generations):
        # Ping-Pong entre as duas memórias partilhadas
        if gen % 2 == 0:
            read_arr, write_arr = arr_a, arr_b
        else:
            read_arr, write_arr = arr_b, arr_a

        for r in range(start_row, end_row):
            row_offset = r * cols
            for c in range(cols):
                idx = row_offset + c

                # Conta vizinhos consultando o array de leitura
                live_neighbors = _count_neighbors(read_arr, r, c, rows, cols)

                # Aplica as regras e escreve no array de escrita
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

        # 2. SINCRONIZAÇÃO: Todos os workers esperam aqui antes de começarem a próxima geração
        barrier.wait()


def game_of_life_parallel(grid: list, generations: int, workers: int) -> list:
    """
    Simula a evolução da grelha recorrendo a múltiplos workers.

    :param grid: Matriz 2D inicial.
    :param generations: Número de gerações.
    :param workers: Número de processos em paralelo.
    :return: Matriz 2D final.
    """
    if not grid or not grid[0]:
        return grid

    rows = len(grid)
    cols = len(grid[0])

    # Se o número de workers exceder o número de linhas, rebaixamos para evitar workers ociosos
    workers = min(workers, rows)

    if workers <= 1:
        return game_of_life_sequential(grid, generations)

    # Criação de memórias partilhadas puras (RawArray). 
    # Não precisam de Locks porque os workers nunca escrevem nas linhas uns dos outros.
    arr_a = mp.RawArray(ctypes.c_byte, rows * cols)
    arr_b = mp.RawArray(ctypes.c_byte, rows * cols)

    # Inicialização da primeira grelha
    for r in range(rows):
        for c in range(cols):
            arr_a[r * cols + c] = grid[r][c]

    # Barreira onde 'workers' processos terão de se encontrar no fim de cada geração
    barrier = mp.Barrier(workers)
    processes = []

    # Arranque dos workers
    for i in range(workers):
        p = mp.Process(
            target=_worker_gol,
            args=(i, workers, rows, cols, arr_a, arr_b, generations, barrier)
        )
        p.start()
        processes.append(p)

    # Esperar que todos terminem a totalidade das gerações
    for p in processes:
        p.join()

    # O array que contém o resultado final depende do número (par/ímpar) de gerações
    final_arr = arr_a if generations % 2 == 0 else arr_b

    # Reconstrói a grelha final em formato 2D (Lista de Listas) para retornar ao Servidor
    final_grid = []
    for r in range(rows):
        start_idx = r * cols
        final_grid.append(list(final_arr[start_idx: start_idx + cols]))

    return final_grid