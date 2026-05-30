import gc
import multiprocessing as mp
import time as time_module

MODO_EXPLORAR = 0   
MODO_REFINAR = 1    
MODO_PERSEGUIR = 2  

def time():
  return time_module.time()

def is_prime(n: int) -> bool:
  if n < 2: return False
  if n in (2, 3): return True
  if n % 2 == 0 or n % 3 == 0: return False
  divisor = 5
  while divisor * divisor <= n:
    if n % divisor == 0 or n % (divisor + 2) == 0:
      return False
    divisor += 6
  return True

def _garantir_impar(n: int) -> int:
  return n if n % 2 != 0 else n + 1

# CORREÇÃO 3: Função para garantir que o STEP é sempre par!
def _garantir_par(n: int) -> int:
  return n if n % 2 == 0 else n + 1

def _alinhar_acima_do_maximo(global_max: int, candidato: int) -> int:
  if global_max <= candidato:
    return candidato
  return _garantir_impar(global_max + 2)

def _limites_tempo(timeout: float):
  if timeout <= 5.0: return 16, 4
  if timeout <= 10.0: return 17, 2
  return 18, 1

def _atribuir_faixa_worker(worker_id, num_workers, mag_min, mag_count, max_magnitude, range_divisor):
  # CORREÇÃO 2: Se for 1 worker, atira-o para o Topo (não para a casa dos milhões!)
  if num_workers == 1:
      return max_magnitude - 1, True, 1, 0, 0

  tail_hunter = False
  workers_na_faixa = 1
  sub_id = 0
  worker_offset = 0

  if num_workers <= mag_count:
    magnitude = mag_min + min(worker_id, mag_count - 1)
    divisor = num_workers * range_divisor
    worker_offset = (10 ** magnitude) // divisor * worker_id
  elif worker_id < mag_count:
    magnitude = mag_min + worker_id
    divisor = mag_count * range_divisor
    worker_offset = (10 ** magnitude) // divisor * worker_id
  else:
    tail_hunter = True
    overflow = worker_id - mag_count
    magnitude = max_magnitude - (overflow % 2)
    workers_na_faixa = num_workers - mag_count
    sub_id = overflow

  return magnitude, tail_hunter, workers_na_faixa, sub_id, worker_offset

def _candidato_inicial(magnitude, top_tier, worker_id, sub_id, worker_offset, start_time):
  base = 10 ** magnitude
  teto = base * 10
  salt = int((start_time % 1.0) * 1_000_003)
  slot = (worker_id + 1) * 1_000_003 + (sub_id + 1) * 2_000_003 + salt

  if top_tier:
    inicio = base + base // 8
    fim = base * 4
    dispersao = (slot % max(1, (fim - inicio) // 2)) * 2
    candidato = inicio + dispersao + worker_offset + 1
  else:
    inicio = base + base // 4
    largura = (base * 7) // 10
    dispersao = (slot % max(1, largura // 2)) * 2 + worker_offset
    candidato = inicio + dispersao + 1

  if candidato >= teto:
    candidato = base + worker_offset + 1

  band_lo = inicio if top_tier else 0
  band_hi = fim if top_tier else teto
  return _garantir_impar(candidato), base, teto, band_lo, band_hi

def _step_inicial(magnitude, timeout_duration, workers_na_faixa):
  fator_mag = 2 ** max(0, magnitude - 10)
  fator_tempo = 1.0 + (3.0 / max(timeout_duration, 1.0))
  fator_workers = 1.0 + (workers_na_faixa / 20.0)
  step = int(2 * fator_mag * fator_tempo * fator_workers)
  
  # CORREÇÃO 3: Step tem de ser PAR
  step = _garantir_par(step) 
  if step < 2: step = 2

  limite = 5000
  if timeout_duration <= 5.0:
    if magnitude >= 14: limite = 600
    elif magnitude >= 12: limite = 1500
    elif magnitude >= 10: limite = 3000
  return min(step, limite)

def _worker_busca_primos(worker_id, num_workers, start_time, end_time,
                         max_value, stop_flag, time_found):
  gc.disable()
  local_time = time
  testar = is_prime

  duracao = max(end_time - start_time, 1e-9)
  max_magnitude, range_divisor = _limites_tempo(duracao)
  mag_min = 6
  mag_count = max_magnitude - mag_min + 1

  magnitude, tail_hunter, workers_na_faixa, sub_id, worker_offset = _atribuir_faixa_worker(
    worker_id, num_workers, mag_min, mag_count, max_magnitude, range_divisor,
  )
  top_tier = tail_hunter or magnitude >= max_magnitude - 1

  candidato, base, teto, band_lo, band_hi = _candidato_inicial(
    magnitude, top_tier, worker_id, sub_id, worker_offset, start_time,
  )

  step = _step_inicial(magnitude, duracao, workers_na_faixa)
  step_inicial = step
  potencia_decay = 2.0 if magnitude >= 12 else 1.0
  modo = MODO_EXPLORAR

  progresso_perseguir = 0.38 if top_tier else 0.62
  progresso_refinar = 0.42 if magnitude >= 14 else 0.34
  progresso_fino = 0.82

  max_global = max_value.get_obj()
  parar = stop_flag.get_obj()
  tempo_encontrado = time_found.get_obj()
  lock_max = max_value.get_lock

  inv_duracao = 1.0 / duracao
  intervalo_check = max(512 if top_tier else 2048, step)
  contador_check = intervalo_check
  contador_sync = 32 if top_tier else 256

  while True:
    if top_tier:
      contador_sync -= 1
      if contador_sync <= 0:
        contador_sync = 32
        candidato = _alinhar_acima_do_maximo(max_global.value, candidato)

    if testar(candidato):
      agora = local_time()
      if agora >= end_time:
        break
      melhor = max_global.value
      if candidato > melhor:
        with lock_max():
          if candidato > max_global.value:
            max_global.value = candidato
            tempo_encontrado.value = agora - start_time
        if top_tier:
          modo = MODO_PERSEGUIR
        elif modo == MODO_EXPLORAR and candidato >= base:
          modo = MODO_REFINAR
          step = 2
          intervalo_check = 2048

    candidato += step
    if candidato >= teto:
      break

    contador_check -= 1
    if contador_check > 0:
      continue
    contador_check = intervalo_check

    if parar.value: break
    agora = local_time()
    if agora >= end_time: break

    melhor = max_global.value
    if melhor >= teto: break
    candidato = _alinhar_acima_do_maximo(melhor, candidato)

    progresso = (agora - start_time) * inv_duracao
    progresso = max(0.0, min(1.0, progresso))

    if top_tier and progresso >= progresso_fino:
      if melhor >= base:
        candidato = _alinhar_acima_do_maximo(melhor, candidato)
        modo = MODO_REFINAR
        step = 2
        intervalo_check = 256
        continue
      if candidato >= band_hi:
        candidato = _garantir_impar(band_lo)
        modo = MODO_PERSEGUIR
        continue

    if top_tier and progresso >= progresso_perseguir:
      modo = MODO_PERSEGUIR

    if modo == MODO_PERSEGUIR:
      candidato = _alinhar_acima_do_maximo(melhor, candidato)
      espaco = teto - candidato
      if espaco > 2:
        tempo_restante = max(0.04, 1.0 - progresso)
        salto = int(espaco / (4 + 10 * tempo_restante))
        salto = max(2, min(salto, 200_000))
        # CORREÇÃO 3: Salto par no modo perseguir
        step = _garantir_par(salto) 
        intervalo_check = max(128, step // 4)
      else:
        modo = MODO_REFINAR
        step = 2
        intervalo_check = 512
      continue

    if modo == MODO_EXPLORAR and progresso >= progresso_refinar and not top_tier:
      modo = MODO_REFINAR
      step = 2
      intervalo_check = 2048
      continue

    if modo == MODO_REFINAR:
      continue

    ajustado = max(0.0, (progresso - 0.15) / 0.85)
    decay = (1.0 - ajustado) ** potencia_decay
    novo_step = int(step_inicial * decay) + 2
    novo_step = min(novo_step, step_inicial)
    
    # CORREÇÃO 3: Step par no modo explorar
    step = max(2, _garantir_par(novo_step))
    intervalo_check = max(2048, step)

def find_max_prime_parallel(timeout: int, workers: int, return_stats: bool = False):
  max_value = mp.Value('Q', 2)
  stop_flag = mp.Value('b', False)
  time_found = mp.Value('d', 0.0)

  inicio = time()
  fim = inicio + float(timeout)
  args_comuns = (workers, inicio, fim, max_value, stop_flag, time_found)

  processos = []
  for i in range(workers):
    p = mp.Process(target=_worker_busca_primos, args=(i, *args_comuns), daemon=True)
    p.start()
    processos.append(p)

  time_module.sleep(float(timeout))
  stop_flag.value = True

  for p in processos:
    p.join(timeout=0.1)
    if p.is_alive():
      p.terminate()

  if return_stats:
    return max_value.value, time_found.value, time() - inicio
  return max_value.value

def find_max_prime_sequential(timeout: int) -> int:
  fim = time() + timeout
  max_primo = 2
  candidato = 3
  a_cada = 4096
  contador = a_cada

  while True:
    contador -= 1
    if contador == 0:
      contador = a_cada
      if time() >= fim:
        break

    if is_prime(candidato):
      max_primo = candidato
    candidato += 2

  return max_primo