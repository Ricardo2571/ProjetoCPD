"""
Módulo Primos
Procura do maior número primo dentro de um limite temporal (Sequencial e Paralelo).
"""

import gc
import multiprocessing as mp
import time as time_module

# Modos de pesquisa da equipa e constantes de dispersão pseudoaleatória
MODE_EXPLORE, MODE_REFINE, MODE_CHASE = 0, 1, 2
DISPERSAO_A, DISPERSAO_B = 1_000_003, 2_000_003

def is_prime(n: int) -> bool:
    """
    Verifica a primalidade de um dado número inteiro utilizando o metodo otimizado (6k +/- 1).

    Args:
        n (int): O número natural a testar.

    Returns:
        bool: True se o número for primo, False caso contrário.
    """
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

def garantir_impar(n: int) -> int:
    """
    Garante que o número a testar é ímpar, evitando iterar por números pares que não são primos.

    Args:
        n (int): O número base.

    Returns:
        int: O próprio número (se for ímpar) ou o número seguinte (se for par).
    """
    return n if n % 2 != 0 else n + 1

def garantir_par(n: int) -> int:
    """
    Garante que o salto entre iterações é sempre um número par.

    Args:
        n (int): O tamanho do salto base.

    Returns:
        int: Um salto par.
    """
    return n if n % 2 == 0 else n + 1

def saltar_acima_do_recorde(recorde_global: int, candidato: int) -> int:
    """
    Ajusta o candidato do worker atual para o próximo número ímpar disponível
    acima do recorde partilhado, evitando repetição de processamento inferior.

    Args:
        recorde_global (int): O maior primo atualmente registado em memória partilhada.
        candidato (int): O número que o worker estava a testar.

    Returns:
        int: O novo valor alvo ajustado.
    """
    return candidato if recorde_global <= candidato else garantir_impar(recorde_global + 2)

def limites_de_tempo(tempo_total: float) -> tuple:
    """
    Define a grandeza matemática máxima baseando-se no tempo disponível, para
    balancear o ponto de partida sem exceder o timeout desnecessariamente.

    Args:
        tempo_total (float): O tempo limite total providenciado (em segundos).

    Returns:
        tuple: (potência de grandeza máxima, multiplicador de dispersão).
    """
    return (16, 4) if tempo_total <= 5.0 else ((17, 2) if tempo_total <= 10.0 else (18, 1))

def atribuir_faixa_worker(id_worker: int, total_workers: int, mag_min: int, mag_contagem: int, mag_max: int, divisor_faixa: int) -> tuple:
    """
    Distribui os workers por diferentes faixas de valores numéricos para cobrir terreno de forma otimizada.

    Args:
        id_worker (int): ID único do worker.
        total_workers (int): Total de workers na pool.
        mag_min (int): Magnitude mínima admissível (ex: 10^6).
        mag_contagem (int): Magnitude relativa atual na distribuição.
        mag_max (int): Magnitude máxima estipulada pelo timeout.
        divisor_faixa (int): Redutor de magnitude.

    Returns:
        tuple: (magnitude base do worker, flag indicando se é top tier, total de workers na faixa, sub_id na faixa, offset matemático)
    """
    if total_workers == 1: return mag_max - 1, True, 1, 0, 0
    if id_worker < mag_contagem:
        mag = mag_min + (min(id_worker, mag_contagem - 1) if total_workers <= mag_contagem else id_worker)
        div = total_workers if total_workers <= mag_contagem else mag_contagem
        return mag, False, 1, 0, ((10 ** mag) // (div * divisor_faixa)) * id_worker

    # Os workers extra atuam como ajuda na zona de topo (top tier)
    excesso = id_worker - mag_contagem
    return mag_max - (excesso % 2), True, total_workers - mag_contagem, excesso, 0

def calcular_ponto_partida(mag: int, e_topo: bool, id_worker: int, sub_id: int, offset: int, tempo_inicio: float) -> tuple:
    """
    Calcula o ponto numérico de arranque pseudoaleatório para garantir que múltiplos
    workers não sobrepõem os seus testes matemáticos.

    Args:
        mag (int): Potência/Magnitude na qual operar.
        e_topo (bool): Indica se o worker está alocado à banda mais alta.
        id_worker (int), sub_id (int), offset (int): Identificadores de distribuição.
        tempo_inicio (float): Timestamp base para semente (seed) aleatória.

    Returns:
        tuple: (Candidato de arranque, base da grandeza, teto máximo, limite inferior e superior)
    """
    base, teto = 10 ** mag, 10 ** (mag + 1)
    slot = (id_worker + 1) * DISPERSAO_A + (sub_id + 1) * DISPERSAO_B + int((tempo_inicio % 1.0) * DISPERSAO_A)

    if e_topo:
        inicio_faixa, fim_faixa = base + (base // 8), base * 4
        candidato = inicio_faixa + ((slot % max(1, (fim_faixa - inicio_faixa) // 2)) * 2) + offset + 1
        lim_inf, lim_sup = inicio_faixa, fim_faixa
    else:
        inicio_faixa, fim_faixa = base + (base // 4), teto
        candidato = inicio_faixa + ((slot % max(1, (base * 7) // 20)) * 2) + offset + 1
        lim_inf, lim_sup = 0, teto

    return garantir_impar(candidato if candidato < teto else base + offset + 1), base, teto, lim_inf, lim_sup

def calcular_salto_inicial(mag: int, duracao: float, workers_na_faixa: int) -> int:
    """
    Define o tamanho do gap/salto (step) entre iterações numéricas, adequando-o ao tempo e recursos.

    Args:
        mag (int): A grandeza a operar.
        duracao (float): Tempo total disponível.
        workers_na_faixa (int): Total de workers alocados a este segmento numérico.

    Returns:
        int: O intervalo/salto de iteração.
    """
    salto = int(2 * (2 ** max(0, mag - 10)) * (1.0 + (3.0 / max(duracao, 1.0))) * (1.0 + (workers_na_faixa / 20.0)))
    salto = max(2, garantir_par(salto))
    limite = (600 if mag >= 14 else (1500 if mag >= 12 else 3000)) if duracao <= 5.0 else 5000
    return max(2, min(salto, limite))

def worker_find_primes(id_worker: int, total_workers: int, tempo_inicio: float, tempo_fim: float, maximo_partilhado, flag_paragem, tempo_encontrado) -> None:
    """
    Função (processo) alvo que realiza a travessia e computação adaptativa na busca de primos (Modos EXPLORE, REFINE, CHASE).

    Args:
        id_worker (int): ID alocado ao worker.
        total_workers (int): Número de processos paralelos disponíveis.
        tempo_inicio (float): Timestamp de arranque.
        tempo_fim (float): Timestamp do prazo limite.
        maximo_partilhado (multiprocessing.Value): Recurso partilhado do maior primo.
        flag_paragem (multiprocessing.Value): Boolean partilhado que emite sinal de interrupção aos workers.
        tempo_encontrado (multiprocessing.Value): Registo do tempo (em float) do último primo.
    """
    gc.disable() # Desliga a limpeza de memória automática para focar os ciclos estritamente na CPU
    duracao = max(tempo_fim - tempo_inicio, 1e-9)
    inv_duracao = 1.0 / duracao

    mag_max, divisor_faixa = limites_de_tempo(duracao)
    mag, e_topo, workers_faixa, sub_id, offset = atribuir_faixa_worker(id_worker, total_workers, 6, mag_max - 5, mag_max, divisor_faixa)
    candidato, base, teto, lim_inf, lim_sup = calcular_ponto_partida(mag, e_topo, id_worker, sub_id, offset, tempo_inicio)

    salto_inicial = salto = calcular_salto_inicial(mag, duracao, workers_faixa)
    decaimento, modo_atual = (2.0 if mag >= 12 else 1.0), MODE_EXPLORE
    gatilho_chase, gatilho_refine, gatilho_final = (0.38 if e_topo else 0.62), (0.42 if mag >= 14 else 0.34), 0.82

    # Acesso rápido às variáveis na memória partilhada
    recorde_global = maximo_partilhado.get_obj()
    sinal_paragem = flag_paragem.get_obj()
    tempo_recorde = tempo_encontrado.get_obj()
    trinco_memoria = maximo_partilhado.get_lock

    # Intervalos para consultar o tempo (evita o dispendioso overhead de chamar a função time() a cada iteração)
    intervalo_verificacao = contador_verificacao = max(512 if e_topo else 2048, salto)
    contador_sincronizacao = 32 if e_topo else 256

    while True:
        if e_topo:
            contador_sincronizacao -= 1
            if contador_sincronizacao <= 0:
                contador_sincronizacao, candidato = 32, saltar_acima_do_recorde(recorde_global.value, candidato)

        if is_prime(candidato):
            tempo_atual = time_module.time()
            if tempo_atual >= tempo_fim: break # Aborta atempadamente se o tempo já tiver esgotado
            if candidato > recorde_global.value:
                with trinco_memoria():
                    if candidato > maximo_partilhado.value:
                        maximo_partilhado.value, tempo_recorde.value = candidato, tempo_atual - tempo_inicio
                # Adapta a estratégia se encontrar um novo recorde que altere o seu comportamento ideal
                if e_topo: modo_atual = MODE_CHASE
                elif modo_atual == MODE_EXPLORE and candidato >= base: modo_atual, salto, intervalo_verificacao = MODE_REFINE, 2, 2048

        candidato += salto
        if candidato >= teto: break

        contador_verificacao -= 1
        if contador_verificacao > 0: continue

        contador_verificacao = intervalo_verificacao
        tempo_atual = time_module.time()

        if sinal_paragem.value or tempo_atual >= tempo_fim or recorde_global.value >= teto: break

        candidato = saltar_acima_do_recorde(recorde_global.value, candidato)
        progresso = max(0.0, min(1.0, (tempo_atual - tempo_inicio) * inv_duracao))

        if e_topo and progresso >= gatilho_final:
            if recorde_global.value >= base:
                candidato, modo_atual, salto, intervalo_verificacao = saltar_acima_do_recorde(recorde_global.value, candidato), MODE_REFINE, 2, 256
                continue
            if candidato >= lim_sup:
                candidato, modo_atual = garantir_impar(lim_inf), MODE_CHASE
                continue

        if e_topo and progresso >= gatilho_chase: modo_atual = MODE_CHASE

        if modo_atual == MODE_CHASE:
            candidato = saltar_acima_do_recorde(recorde_global.value, candidato)
            espaco_livre = teto - candidato
            if espaco_livre > 2: # Aumenta a agressividade (salto) se estiver próximo do final temporal
                salto = garantir_par(max(2, min(int(espaco_livre / (4 + 10 * max(0.04, 1.0 - progresso))), 200_000)))
                intervalo_verificacao = max(128, salto // 4)
            else:
                modo_atual, salto, intervalo_verificacao = MODE_REFINE, 2, 512
            continue

        if modo_atual == MODE_EXPLORE and progresso >= gatilho_refine and not e_topo:
            modo_atual, salto, intervalo_verificacao = MODE_REFINE, 2, 2048
            continue

        if modo_atual == MODE_REFINE: continue

        # Decaimento progressivo do tamanho do salto durante a fase de exploração normal
        salto = max(2, garantir_par(min(int(salto_inicial * ((1.0 - max(0.0, (progresso - 0.15) / 0.85)) ** decaimento)) + 2, salto_inicial)))
        intervalo_verificacao = max(2048, salto)

def find_max_prime_parallel(timeout: int, workers: int) -> tuple:
    """
    Inicia a procura paralela gerindo a pool de multiprocessos e sincronizando resultados.

    Args:
        timeout (int): Tempo limite máximo alocado à computação global (em segundos).
        workers (int): Número de processos filhos a alocar.

    Returns:
        tuple: (Maior primo encontrado (int), Instante da descoberta relativa (float))
    """
    maximo_partilhado, sinal_paragem, tempo_encontrado = mp.Value('Q', 2), mp.Value('b', False), mp.Value('d', 0.0)
    tempo_inicio = time_module.time()

    argumentos = (workers, tempo_inicio, tempo_inicio + float(timeout), maximo_partilhado, sinal_paragem, tempo_encontrado)
    processos = [mp.Process(target=worker_find_primes, args=(i, *argumentos), daemon=True) for i in range(workers)]

    for p in processos: p.start()
    time_module.sleep(float(timeout)) # A thread principal aguarda
    sinal_paragem.value = True

    for p in processos:
        p.join(timeout=0.1)
        if p.is_alive(): p.terminate()

    return maximo_partilhado.value, tempo_encontrado.value

def find_max_prime_sequential(timeout: int) -> tuple:
    """
    Inicia a procura sequencial tradicional (Single-Thread) do maior número primo.

    Args:
        timeout (int): Tempo limite de procura (em segundos).

    Returns:
        tuple: (Maior primo encontrado (int), Instante da descoberta relativa (float))
    """
    tempo_inicio, tempo_fim = time_module.time(), time_module.time() + float(timeout)
    maior_primo, candidato, tempo_encontrado, intervalo_verificacao = 2, 3, 0.0, 20
    contador_verificacao = intervalo_verificacao

    while True:
        contador_verificacao -= 1
        if contador_verificacao <= 0:
            contador_verificacao = intervalo_verificacao
            if time_module.time() >= tempo_fim: break # Timeout atingido

        if is_prime(candidato):
            tempo_atual = time_module.time()
            if tempo_atual >= tempo_fim: break
            maior_primo, tempo_encontrado = candidato, tempo_atual - tempo_inicio

        candidato += 2

    return maior_primo, tempo_encontrado