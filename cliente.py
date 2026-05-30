import socket
import json

class RPCClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port

    def call(self, method: str, params: dict):
        """Envia o pedido ao servidor usando o formato estrito."""
        request = {
            "method": method,
            "params": params
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.send((json.dumps(request) + '\n').encode('utf-8'))

                # Receber resposta
                response_str = ""
                while '\n' not in response_str:
                    chunk = sock.recv(4096).decode('utf-8')
                    if not chunk: break
                    response_str += chunk

                response = json.loads(response_str.strip())
                if "error" in response:
                    print(f"ERRO DO SERVIDOR: {response['error']}")
                    return None
                return response.get("result")
        except ConnectionRefusedError:
            print("Erro: Nao foi possivel conectar ao servidor.")
            return None

def main():
    client = RPCClient()

    while True:
        print("\n--- MENU RPC ---")
        print("1. Listar Metodos")
        print("2. Testar Primalidade (is_prime)")
        print("3. Maior Primo (timeout + workers)")
        print("4. Game of life(Simular)")
        print("5. Game of life(Visualizar)")
        print("6. Sair")

        escolha = input("Escolha uma opcao: ")

        if escolha == '1':
            metodos = client.call("list_methods", {})
            for m in metodos: print(m)

        elif escolha == '2':
            n = int(input("Introduza um numero: "))
            res = client.call("is_prime", {"n": n})
            print(f"O numero {n} e primo? {res}")


        elif escolha == '3':

            timeout = float(input("Tempo limite por teste (segundos): "))

            max_workers = int(input("Testar de 1 ate quantos workers? (ex: 6): "))

            repeticoes = int(input("Repeticoes por cada configuracao de worker: "))

            print("\n" + "=" * 115)

            print(" INICIAR BATERIA DE TESTES DE PERFORMANCE ".center(115, "="))

            print("=" * 115)

            # Loop pelos workers (de 1 até max_workers)

            for w in range(1, max_workers + 1):

                print(f"\n[{w} WORKER(S)] " + "-" * 101)

                # Cabeçalho da tabela com todas as colunas pedidas

                print(
                    f"{'Tent.':<6} | {'Timeout':<8} | {'Tempo Real':<11} | {'T. Último Primo':<16} | {'T. Excesso':<11} | {'Dígitos':<8} | {'Primo Encontrado'}")

                print("-" * 115)

                for r in range(1, repeticoes + 1):

                    res = client.call("find_max_prime", {"timeout": timeout, "workers": w})

                    if res:
                        p = res.get("max_prime")

                        t_found = res.get("time_found")

                        t_total = res.get("total_time")

                        # Tempo em Excesso (overhead do sistema operatório e da rede)

                        excesso = t_total - timeout

                        digitos = len(str(p))

                        # Imprimir linha formatada

                        print(
                            f"{r:<6} | {timeout:<8.2f} | {t_total:<11.4f} | {t_found:<16.4f} | {excesso:<11.4f} | {digitos:<8} | {p}")

            print("\n" + "=" * 115)

            print(" TESTES CONCLUÍDOS ".center(115, "="))

            print("=" * 115 + "\n")



        elif escolha == '4':

            print("\n--- Benchmark Game of Life (Simulação) ---")

            # 1. Recolha de parâmetros

            dimensao = int(input("Tamanho da grelha (ex: 500 para 500x500): "))

            geracoes = int(input("Numero de geracoes a simular: "))

            max_workers = int(input("Testar de 1 ate quantos workers? (ex: 8): "))

            repeticoes = int(input("Repeticoes por cada configuracao de worker: "))

            print(f"\nA gerar matriz base aleatoria de {dimensao}x{dimensao} (20% vida)...")

            import random

            import time

            # Geração da grelha ÚNICA para todos os testes (Requisito do Enunciado)

            grelha_base = [[1 if random.random() < 0.2 else 0 for _ in range(dimensao)] for _ in range(dimensao)]

            print("\n" + "=" * 90)

            print(" INICIAR BATERIA DE TESTES GOL ".center(90, "="))

            print("=" * 90)

            tempo_base_1_worker = None

            for w in range(1, max_workers + 1):

                print(f"\n[{w} WORKER(S)] " + "-" * 76)

                # Colunas relevantes para as estatísticas do Game of Life

                print(f"{'Tent.':<6} | {'Gerações':<10} | {'Dimensão':<12} | {'Tempo (s)':<12} | {'Speedup':<10}")

                print("-" * 90)

                tempos_w = []

                for r in range(1, repeticoes + 1):

                    start_t = time.time()

                    # Chama o RPC com a mesma grelha base

                    res = client.call("game_of_life", {

                        "grid": grelha_base,

                        "generations": geracoes,

                        "workers": w

                    })

                    end_t = time.time()

                    if res:

                        t_exec = end_t - start_t

                        tempos_w.append(t_exec)

                        # Cálculo dinâmico do Speedup

                        speedup_str = "---"

                        if tempo_base_1_worker is not None:

                            speedup = tempo_base_1_worker / t_exec

                            speedup_str = f"{speedup:.2f}x"

                        elif w == 1:

                            speedup_str = "1.00x"  # A base é sempre 1x

                        dim_str = f"{dimensao}x{dimensao}"

                        print(f"{r:<6} | {geracoes:<10} | {dim_str:<12} | {t_exec:<12.4f} | {speedup_str:<10}")

                    else:

                        print("Erro na comunicacao com o servidor.")

                        break

                # Guarda o tempo médio de 1 worker para calcular o speedup dos restantes

                if w == 1 and tempos_w:
                    tempo_base_1_worker = sum(tempos_w) / len(tempos_w)

            print("\n" + "=" * 90)

            print(" TESTES CONCLUÍDOS ".center(90, "="))

            print("=" * 90 + "\n")





        elif escolha == '5':

            print("\n--- Teste Game of Life Visual ---")

            print("A abrir a janela gráfica... (Pode continuar a usar o menu!)")

            import subprocess

            import sys

            import os

            ambiente = os.environ.copy()

            ambiente["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

            try:

                # O segredo do Windows para não abrir a janela preta do CMD!

                CREATE_NO_WINDOW = 0x08000000

                subprocess.Popen(

                    [sys.executable, "visualizador.py"],

                    stdout=subprocess.DEVNULL,

                    stderr=subprocess.DEVNULL,

                    stdin=subprocess.DEVNULL,

                    creationflags=CREATE_NO_WINDOW,  # <-- Impede a criação da janela extra

                    env=ambiente

                )

            except FileNotFoundError:

                print("Erro: O ficheiro 'visualizador.py' nao foi encontrado na mesma pasta.")

        elif escolha == '6':
            break

if __name__ == '__main__':
    main()