"""
Módulo Cliente RPC
Fornece uma interface de consola (CLI) interativa para envio de parâmetros e
baterias de benchmark contra o servidor RPC.
"""

import json
import random
import socket
import time
from typing import Any, Dict, Optional


class RPCClient:
    """
    Classe para instanciar a comunicação e envios JSON ao Servidor.
    """

    def __init__(self, host: str = 'localhost', port: int = 5000):
        """
        Inicializa um descritor de cliente RPC.

        Args:
            host (str, opcional): Host de destino (default: 'localhost').
            port (int, opcional): Porta de destino TCP (default: 5000).
        """
        self.host = host
        self.port = port

    def call(self, method: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Gera a framework de rede, conecta-se, transmite o pedido estruturado
        e aguarda descodificando a resposta com tratamento robusto de falhas.

        Args:
            method (str): A string equivalente à função no servidor.
            params (Dict): Dicionário de argumentos da função.

        Returns:
            Optional[Any]: O valor devolvido pela função do servidor, ou None em caso de erro.
        """
        request = {
            "method": method,
            "params": params
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.send((json.dumps(request) + '\n').encode('utf-8'))

                response_str = ""
                while '\n' not in response_str:
                    chunk = sock.recv(4096).decode('utf-8')
                    if not chunk:
                        break
                    response_str += chunk

                if not response_str.strip():
                    print("Erro de Comunicacao: O servidor fechou a ligacao inesperadamente.")
                    return None

                response = json.loads(response_str.strip())

                if "error" in response:
                    print(f"ERRO DO SERVIDOR: {response['error']}")
                    return None

                return response.get("result")

        except ConnectionRefusedError:
            print("Erro de Ligacao: O servidor nao se encontra ativo ou recusou a conexao.")
            return None
        except json.JSONDecodeError:
            print("Erro de Protocolo: A resposta recebida do servidor nao e um JSON valido.")
            return None
        except OSError as e:
            print(f"Erro de Rede intermedio: {e}")
            return None


def main() -> None:
    """
    Menu principal executado de forma cíclica que lida com a entrada de comandos.

    Returns:
        None
    """
    client = RPCClient()

    while True:
        print("\n--- MENU DE APLICACAO RPC ---")
        print("1. Listar Metodos Disponiveis")
        print("2. Testar Primalidade Individual (is_prime)")
        print("3. Encontrar Maior Primo")
        print("4. Game of Life")
        print("5. BONUS: Game of Life (Visualizador Grafico)")
        print("6. Sair")

        escolha = input("Escolha uma opcao: ")

        if escolha == '1':
            metodos = client.call("list_methods", {})
            if metodos:
                for m in metodos:
                    # Formata os parâmetros de forma limpa como "funcao(param1, param2)" em vez de tuplos nativos
                    params_formatados = ", ".join(m['parametros'])
                    print(f"- {m['nome']}({params_formatados}) -> {m['descricao']}")

        elif escolha == '2':
            try:
                n = input("Introduza um numero natural: ")
                # Envia o input; a validação estrita do tipo será feita também no servidor
                res = client.call("is_prime", {"n": n})
                if res is not None:
                    print(f"O numero {n} e primo? {res}")
            except ValueError:
                print("Por favor, insira um numero inteiro valido.")

        elif escolha == '3':
            try:
                timeout = float(input("Tempo limite por teste (segundos): "))
                max_workers = int(input("Testar de 1 ate quantos workers? (ex: 6): "))
                repeticoes = int(input("Repeticoes por cada configuracao de worker: "))
            except ValueError:
                print("Entrada invalida. Cancelando.")
                continue

            print("\n" + "=" * 115)
            print(" INICIAR BATERIA DE TESTES DE PERFORMANCE (PRIMOS) ".center(115, "="))
            print("=" * 115)

            for w in range(1, max_workers + 1):
                print(f"\n[{w} WORKER(S)] " + "-" * 101)
                print(
                    f"{'Tent.':<6} | {'Timeout':<8} | {'Tempo Real':<11} | {'T. Último Primo':<16} | {'T. Excesso':<11} | {'Digitos':<8} | {'Primo Encontrado'}")
                print("-" * 115)

                for r in range(1, repeticoes + 1):
                    res = client.call("find_max_prime", {"timeout": timeout, "workers": w})
                    if res:
                        p = res.get("max_prime")
                        t_total = res.get("total_time")
                        t_found = res.get("time_found")
                        digitos = len(str(p))
                        excesso = t_total - timeout

                        print(
                            f"{r:<6} | {timeout:<8.2f} | {t_total:<11.4f} | {t_found:<16.4f} | {excesso:<11.4f} | {digitos:<8} | {p}")

            print("\n" + "=" * 115)
            print(" TESTES CONCLUIDOS ".center(115, "="))
            print("=" * 115 + "\n")

        elif escolha == '4':
            print("\n--- Benchmark Game of Life (Analise de Desempenho) ---")
            try:
                dimensao = int(input("Tamanho da grelha (ex: 500 para 500x500): "))
                geracoes = int(input("Numero de geracoes a simular: "))
                max_workers = int(input("Testar de 1 ate quantos workers? (ex: 8): "))
                repeticoes = int(input("Repeticoes por cada configuracao de worker: "))
            except ValueError:
                print("Entrada invalida. Cancelando.")
                continue

            print(f"\nA gerar matriz base aleatoria de {dimensao}x{dimensao} (20% vida)...")
            grelha_base = [[1 if random.random() < 0.2 else 0 for _ in range(dimensao)] for _ in range(dimensao)]

            print("\n" + "=" * 90)
            print(" INICIAR BATERIA DE TESTES GOL ".center(90, "="))
            print("=" * 90)

            tempo_base_1_worker = None

            for w in range(1, max_workers + 1):
                print(f"\n[{w} WORKER(S)] " + "-" * 76)
                print(f"{'Tent.':<6} | {'Geracoes':<10} | {'Dimensao':<12} | {'Tempo (s)':<12} | {'Speedup':<10}")
                print("-" * 90)

                tempos_w = []
                for r in range(1, repeticoes + 1):
                    start_t = time.time()

                    res = client.call("game_of_life", {
                        "grid": grelha_base,
                        "generations": geracoes,
                        "workers": w
                    })

                    end_t = time.time()

                    if res:
                        t_exec = end_t - start_t
                        tempos_w.append(t_exec)

                        speedup_str = "---"
                        if tempo_base_1_worker is not None:
                            speedup = tempo_base_1_worker / t_exec
                            speedup_str = f"{speedup:.2f}x"
                        elif w == 1:
                            speedup_str = "1.00x"

                        dim_str = f"{dimensao}x{dimensao}"
                        print(f"{r:<6} | {geracoes:<10} | {dim_str:<12} | {t_exec:<12.4f} | {speedup_str:<10}")
                    else:
                        print("Erro na comunicacao com o servidor.")
                        break

                if w == 1 and tempos_w:
                    tempo_base_1_worker = sum(tempos_w) / len(tempos_w)

            print("\n" + "=" * 90)
            print(" TESTES CONCLUIDOS ".center(90, "="))
            print("=" * 90 + "\n")

        elif escolha == '5':
            print("\n--- Teste Game of Life Visual ---")
            print("A abrir a janela grafica... (Pode continuar a usar o menu de texto!)")
            import os
            import subprocess
            import sys

            ambiente = os.environ.copy()
            ambiente["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

            try:
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    [sys.executable, "visualizador.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW,
                    env=ambiente
                )
            except FileNotFoundError:
                print("Erro: O ficheiro 'visualizador.py' nao foi encontrado na mesma pasta.")

        elif escolha == '6':
            print("A encerrar o cliente...")
            break

        else:
            print("Opcao invalida.")


if __name__ == '__main__':
    main()