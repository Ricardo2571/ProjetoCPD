"""
Módulo Game of Life
Implementa o autómato celular de John Conway com abordagens sequencial e paralela.
Utiliza Shared Memory (RawArray) C-Types para eliminar overhead de IPC Serialization.
"""

import multiprocessing as mp
import ctypes

def game_of_life_sequential(grid: list, generations: int) -> list:
    if not grid or not grid[0]:
        return grid

    rows = len(grid)
    cols = len(grid[0])
    # Achatamento da grelha maximiza a localidade em Cache (Data Locality)
    current_grid = [val for row in grid for val in row]
    next_grid = [0] * (rows * cols)

    for _ in range(generations):
        for r in range(rows):
            r_min, r_max = max(0, r - 1), min(rows, r + 2)
            row_offset = r * cols

            for c in range(cols):
                c_min, c_max = max(0, c - 1), min(cols, c + 2)
                idx = row_offset + c

                # Inlining da contagem de vizinhos para evitar Function Call Overhead
                vizinhos = 0
                for i in range(r_min, r_max):
                    i_offset = i * cols
                    for j in range(c_min, c_max):
                        if current_grid[i_offset + j]:
                            vizinhos += 1

                estado_atual = current_grid[idx]
                if estado_atual:
                    vizinhos -= 1 # Desconta a própria célula se estava viva
                    next_grid[idx] = 1 if (vizinhos == 2 or vizinhos == 3) else 0
                else:
                    next_grid[idx] = 1 if vizinhos == 3 else 0

        # Swap rápido de referências
        current_grid, next_grid = next_grid, current_grid

    # Reconstrói a grelha 2D final
    return [current_grid[r*cols : (r+1)*cols] for r in range(rows)]

def _worker_gol_otimizado(worker_id: int, num_workers: int, rows: int, cols: int,
                          arr_a, arr_b, generations: int, barrier):
    """Worker de execução paralela utilizando chunking horizontal."""
    chunk = rows // num_workers
    start_row = worker_id * chunk
    end_row = rows if worker_id == num_workers - 1 else (worker_id + 1) * chunk

    for gen in range(generations):
        # Double Buffering (Ping-Pong) para evitar Race Conditions
        read_arr, write_arr = (arr_a, arr_b) if gen % 2 == 0 else (arr_b, arr_a)

        for r in range(start_row, end_row):
            r_min, r_max = max(0, r - 1), min(rows, r + 2)
            row_offset = r * cols

            for c in range(cols):
                c_min, c_max = max(0, c - 1), min(cols, c + 2)
                idx = row_offset + c

                vizinhos = 0
                for i in range(r_min, r_max):
                    i_offset = i * cols
                    for j in range(c_min, c_max):
                        if read_arr[i_offset + j]:
                            vizinhos += 1

                estado_atual = read_arr[idx]
                if estado_atual:
                    vizinhos -= 1
                    write_arr[idx] = 1 if (vizinhos == 2 or vizinhos == 3) else 0
                else:
                    write_arr[idx] = 1 if vizinhos == 3 else 0

        # Barreira restrita: Ninguém avança no tempo sem que o espaço esteja sincronizado
        barrier.wait()

def game_of_life_parallel(grid: list, generations: int, workers: int) -> list:
    if not grid or not grid[0]: return grid

    rows, cols = len(grid), len(grid[0])
    workers = min(workers, rows)

    if workers <= 1:
        return game_of_life_sequential(grid, generations)

    # Memória Partilhada Nativa C (Bypassa o GIL do Python e serialização do Pickle)
    arr_a = mp.RawArray(ctypes.c_byte, rows * cols)
    arr_b = mp.RawArray(ctypes.c_byte, rows * cols)

    for r in range(rows):
        for c in range(cols):
            arr_a[r * cols + c] = grid[r][c]

    barrier = mp.Barrier(workers)
    processes = [
        mp.Process(target=_worker_gol_otimizado, args=(i, workers, rows, cols, arr_a, arr_b, generations, barrier))
        for i in range(workers)
    ]

    for p in processes: p.start()
    for p in processes: p.join()

    final_arr = arr_a if generations % 2 == 0 else arr_b
    return [list(final_arr[r*cols : (r+1)*cols]) for r in range(rows)]