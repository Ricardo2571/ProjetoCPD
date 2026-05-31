"""
Módulo Primos
Procura do maior número primo dentro de um limite temporal.
Versões sequencial e paralela (multiprocessing).
"""

import gc
import multiprocessing as mp
import time as time_module

# Constantes para os modos de busca
MODE_EXPLORE = 0
MODE_REFINE = 1
MODE_CHASE = 2


# ---------------------------------------------------------------------------
# Função obrigatória do enunciado
# ---------------------------------------------------------------------------
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    divisor = 5
    while divisor * divisor <= n:
        if n % divisor == 0 or n % (divisor + 2) == 0:
            return False
        divisor += 6

    return True


# ---------------------------------------------------------------------------
# Funções Matemáticas Auxiliares
# ---------------------------------------------------------------------------
def ensure_odd(n: int) -> int:
    # Garante que o número é ímpar (soma 1 se for par)
    if n % 2 != 0:
        return n
    else:
        return n + 1


def ensure_even(n: int) -> int:
    # Garante que o número (o salto) é par
    if n % 2 == 0:
        return n
    else:
        return n + 1


def align_above_max(global_max: int, candidate: int) -> int:
    # Ajusta o candidato para saltar acima do maior primo já encontrado
    if global_max <= candidate:
        return candidate
    else:
        return ensure_odd(global_max + 2)


def get_time_limits(timeout_duration: float) -> tuple:
    # Define a magnitude máxima da pesquisa com base no tempo disponível
    if timeout_duration <= 5.0:
        return 16, 4
    elif timeout_duration <= 10.0:
        return 17, 2
    else:
        return 18, 1


# ---------------------------------------------------------------------------
# Lógica de Inicialização dos Workers
# ---------------------------------------------------------------------------
def assign_worker_range(worker_id, num_workers, min_magnitude, magnitude_count, max_magnitude, range_divisor):
    # Se houver apenas 1 worker, atira-o para uma magnitude alta mas segura
    if num_workers == 1:
        return max_magnitude - 1, True, 1, 0, 0

    is_top_tier = False
    workers_in_range = 1
    sub_id = 0
    worker_offset = 0

    if worker_id < magnitude_count:
        # Distribui os workers normais pelas diferentes grandezas matemáticas
        if num_workers <= magnitude_count:
            magnitude = min_magnitude + min(worker_id, magnitude_count - 1)
            current_divisor = num_workers
        else:
            magnitude = min_magnitude + worker_id
            current_divisor = magnitude_count

        worker_offset = (10 ** magnitude) // (current_divisor * range_divisor) * worker_id
        return magnitude, False, 1, 0, worker_offset
    else:
        # Os workers "extra" vão ajudar nas zonas mais altas (top tier)
        is_top_tier = True
        overflow = worker_id - magnitude_count
        magnitude = max_magnitude - (overflow % 2)
        workers_in_range = num_workers - magnitude_count
        sub_id = overflow

        return magnitude, is_top_tier, workers_in_range, sub_id, 0


def calculate_initial_candidate(magnitude, is_top_tier, worker_id, sub_id, offset, start_time):
    base = 10 ** magnitude
    ceiling = base * 10

    # Cria uma dispersão aleatória baseada no tempo para os workers não se sobreporem
    salt = int((start_time % 1.0) * 1_000_003)
    slot = (worker_id + 1) * 1_000_003 + (sub_id + 1) * 2_000_003 + salt

    if is_top_tier:
        start_point = base + (base // 8)
        end_point = base * 4
        dispersion_limit = max(1, (end_point - start_point) // 2)
        dispersion = (slot % dispersion_limit) * 2
        candidate = start_point + dispersion + offset + 1

        band_low = start_point
        band_high = end_point
    else:
        start_point = base + (base // 4)
        end_point = ceiling
        dispersion_limit = max(1, (base * 7) // 20)
        dispersion = (slot % dispersion_limit) * 2 + offset
        candidate = start_point + dispersion + 1

        band_low = 0
        band_high = ceiling

    # Previne que o candidato inicial fuja dos limites
    if candidate >= ceiling:
        candidate = base + offset + 1

    return ensure_odd(candidate), base, ceiling, band_low, band_high


def calculate_initial_step(magnitude, timeout_duration, workers_in_range):
    # Define o tamanho do salto (step) entre verificações numéricas
    magnitude_factor = 2 ** max(0, magnitude - 10)
    time_factor = 1.0 + (3.0 / max(timeout_duration, 1.0))
    worker_factor = 1.0 + (workers_in_range / 20.0)

    step = int(2 * magnitude_factor * time_factor * worker_factor)
    step = ensure_even(step)

    if step < 2:
        step = 2

    # Limita o tamanho do salto se o tempo for curto
    step_limit = 5000
    if timeout_duration <= 5.0:
        if magnitude >= 14:
            step_limit = 600
        elif magnitude >= 12:
            step_limit = 1500
        elif magnitude >= 10:
            step_limit = 3000

    result = min(step, step_limit)
    return max(2, result)


# ---------------------------------------------------------------------------
# Worker Paralelo Principal
# ---------------------------------------------------------------------------
def worker_find_primes(worker_id, num_workers, start_time, end_time, shared_max, stop_flag, shared_time_found):
    # Desliga a limpeza de memória automática para ganhar velocidade
    gc.disable()

    duration = max(end_time - start_time, 1e-9)
    max_magnitude, range_divisor = get_time_limits(duration)

    magnitude, is_top_tier, workers_in_range, sub_id, offset = assign_worker_range(
        worker_id, num_workers, 6, max_magnitude - 5, max_magnitude, range_divisor
    )

    candidate, base, ceiling, band_low, band_high = calculate_initial_candidate(
        magnitude, is_top_tier, worker_id, sub_id, offset, start_time
    )

    step = calculate_initial_step(magnitude, duration, workers_in_range)
    initial_step = step

    if magnitude >= 12:
        decay_power = 2.0
    else:
        decay_power = 1.0

    current_mode = MODE_EXPLORE

    # Progresso do tempo para mudar as estratégias
    progress_chase = 0.38 if is_top_tier else 0.62
    progress_refine = 0.42 if magnitude >= 14 else 0.34
    progress_fine = 0.82

    # Variáveis partilhadas
    global_max_obj = shared_max.get_obj()
    stop_flag_obj = stop_flag.get_obj()
    time_found_obj = shared_time_found.get_obj()
    shared_lock = shared_max.get_lock

    inverse_duration = 1.0 / duration

    if is_top_tier:
        check_interval = 512
    else:
        check_interval = 2048

    check_interval = max(check_interval, step)
    check_counter = check_interval

    if is_top_tier:
        sync_counter = 32
    else:
        sync_counter = 256

    # O ciclo principal de procura matemática
    while True:
        # Sincroniza com o melhor valor de x em x iterações
        if is_top_tier:
            sync_counter -= 1
            if sync_counter <= 0:
                sync_counter = 32
                candidate = align_above_max(global_max_obj.value, candidate)

        # Se encontrou um primo...
        if is_prime(candidate):
            current_time = time_module.time()

            if current_time >= end_time:
                break

            best_found = global_max_obj.value

            # Se este primo for o maior de todos até agora...
            if candidate > best_found:
                # Tranca a memória (Lock) e atualiza para que todos saibam
                with shared_lock():
                    if candidate > shared_max.value:
                        shared_max.value = candidate
                        time_found_obj.value = current_time - start_time

                if is_top_tier:
                    current_mode = MODE_CHASE
                elif current_mode == MODE_EXPLORE and candidate >= base:
                    current_mode = MODE_REFINE
                    step = 2
                    check_interval = 2048

        # Prepara o próximo número a testar
        candidate += step

        if candidate >= ceiling:
            break

        # O relógio só é lido a cada X tentativas para poupar CPU
        check_counter -= 1
        if check_counter > 0:
            continue

        check_counter = check_interval
        current_time = time_module.time()

        if stop_flag_obj.value or current_time >= end_time:
            break

        best_found = global_max_obj.value

        if best_found >= ceiling:
            break

        candidate = align_above_max(best_found, candidate)
        progress = (current_time - start_time) * inverse_duration

        if progress < 0.0: progress = 0.0
        if progress > 1.0: progress = 1.0

        # Lógicas de transição consoante o tempo vai acabando
        if is_top_tier and progress >= progress_fine:
            if best_found >= base:
                candidate = align_above_max(best_found, candidate)
                current_mode = MODE_REFINE
                step = 2
                check_interval = 256
                continue

            if candidate >= band_high:
                candidate = ensure_odd(band_low)
                current_mode = MODE_CHASE
                continue

        if is_top_tier and progress >= progress_chase:
            current_mode = MODE_CHASE

        if current_mode == MODE_CHASE:
            candidate = align_above_max(best_found, candidate)
            space_left = ceiling - candidate

            if space_left > 2:
                time_left = max(0.04, 1.0 - progress)
                jump = int(space_left / (4 + 10 * time_left))
                jump = max(2, min(jump, 200_000))

                step = ensure_even(jump)
                check_interval = max(128, step // 4)
            else:
                current_mode = MODE_REFINE
                step = 2
                check_interval = 512
            continue

        if current_mode == MODE_EXPLORE and progress >= progress_refine and not is_top_tier:
            current_mode = MODE_REFINE
            step = 2
            check_interval = 2048
            continue

        if current_mode == MODE_REFINE:
            continue

        # Reduz suavemente o tamanho do salto no modo de exploração
        adjusted_progress = max(0.0, (progress - 0.15) / 0.85)
        decay_factor = (1.0 - adjusted_progress) ** decay_power

        new_step = int(initial_step * decay_factor) + 2
        new_step = min(new_step, initial_step)

        step = max(2, ensure_even(new_step))
        check_interval = max(2048, step)


# ---------------------------------------------------------------------------
# Funções Principais a Expor para o RPC
# ---------------------------------------------------------------------------
def find_max_prime_parallel(timeout: int, workers: int) -> tuple:
    # Memória partilhada
    shared_max = mp.Value('Q', 2)
    stop_flag = mp.Value('b', False)
    shared_time_found = mp.Value('d', 0.0)

    start_time = time_module.time()
    end_time = start_time + float(timeout)

    arguments = (workers, start_time, end_time, shared_max, stop_flag, shared_time_found)

    # Cria os processos
    processes = []
    for i in range(workers):
        p = mp.Process(target=worker_find_primes, args=(i, *arguments), daemon=True)
        processes.append(p)

    # Inicia todos ao mesmo tempo
    for p in processes:
        p.start()

    # A thread principal (servidor) descansa até o tempo acabar
    time_module.sleep(float(timeout))

    # Envia sinal de fecho para todos
    stop_flag.value = True

    # Aguarda a terminação segura (join) e mata quem demorar (terminate)
    for p in processes:
        p.join(timeout=0.1)
        if p.is_alive():
            p.terminate()

    return shared_max.value, shared_time_found.value


def find_max_prime_sequential(timeout: int) -> tuple:
    start_time = time_module.time()
    end_time = start_time + float(timeout)

    max_prime = 2
    candidate = 3

    # 1. Reduzimos o intervalo para evitar que ele fique preso a fazer matemática
    # longos segundos depois de o tempo limite já ter acabado.
    check_interval = 20
    check_counter = check_interval
    time_found = 0.0

    while True:
        check_counter -= 1

        if check_counter == 0:
            check_counter = check_interval

            if time_module.time() >= end_time:
                break

        if is_prime(candidate):
            current_time = time_module.time()

            # 2. Validação super rigorosa: Se encontrou o primo, mas o tempo já
            # tinha acabado, rejeita o número e sai do ciclo imediatamente!
            if current_time >= end_time:
                break

            max_prime = candidate
            time_found = current_time - start_time

        candidate += 2

    return max_prime, time_found