"""
Módulo Servidor RPC
Alojador das instâncias de backend com gestão de pedidos via sockets TCP e parsing JSON.
"""

import socket
import json
import threading
import inspect
import time
from primos import find_max_prime_parallel, is_prime, find_max_prime_sequential
from game_of_life import game_of_life_sequential, game_of_life_parallel

class RPCServer:
    """
    Servidor RPC (Remote Procedure Call) assíncrono capaz de expor métodos internos
    através de uma porta TCP para consumo exterior remoto.
    """

    def __init__(self, host: str = 'localhost', port: int = 5000):
        """
        Inicializa a infraestrutura base do servidor RPC.

        Args:
            host (str, opcional): Hostname ou IP de bind (default: 'localhost').
            port (int, opcional): Porta de escuta (default: 5000).
        """
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None

        self.methods = {
            'find_max_prime': self._find_max_prime,
            'is_prime': self._is_prime,
            'game_of_life': self._game_of_life,
            'list_methods': self._list_methods,
        }

    def _find_max_prime(self, timeout: float, workers: int = 1) -> dict:
        """
        Wrapper do servidor para instanciar o cálculo do maior primo.

        Args:
            timeout (float): Duração total admissível.
            workers (int, opcional): Contagem de paralelismo (default: 1).

        Returns:
            dict: Dicionário contendo os tempos gastos e o maior primo obtido.
        """
        start = time.time()
        if workers > 1:
            p, t_found = find_max_prime_parallel(int(timeout), workers)
        else:
            p, t_found = find_max_prime_sequential(int(timeout))

        total_time = time.time() - start
        return {
            "max_prime": p,
            "time_found": round(t_found, 4),
            "total_time": round(total_time, 4)
        }

    def _is_prime(self, n: int) -> bool:
        """
        Wrapper do servidor para verificar a primalidade individual.

        Args:
            n (int): Número a verificar.

        Returns:
            bool: Validação booleana do fator primo.
        """
        return is_prime(int(n))

    def _game_of_life(self, grid: list, generations: int, workers: int = 1) -> list:
        """
        Wrapper do servidor para instanciar o cálculo do Game Of Life (Conway).

        Args:
            grid (list): Matriz iterável a processar.
            generations (int): Total de ciclos da vida a computar.
            workers (int, opcional): Nível de concorrência (default: 1).

        Returns:
            list: Matriz contendo o estado pós-processado.
        """
        if workers > 1:
            return game_of_life_parallel(grid, int(generations), int(workers))
        return game_of_life_sequential(grid, int(generations))

    def _list_methods(self) -> list:
        """
        Recolhe de forma dinâmica (Reflection) todos os métodos RPC que a classe expõe.

        Returns:
            list: Estrutura de dados contendo nome, argumentos e descrições formatadas.
        """
        lista = []
        for name, func in self.methods.items():
            sig = inspect.signature(func)
            params = [p for p in sig.parameters.keys() if p != 'self']
            desc = func.__doc__ if func.__doc__ else "Executa a operacao correspondente."
            lista.append({"nome": name, "parametros": params, "descricao": desc.strip()})
        return lista

    def _handle_request(self, req: dict) -> dict:
        """
        Efetua o parsing e encaminhamento (dispatch) do pedido JSON RPC válido,
        garantindo a validação estrita de tipos e argumentos.

        Args:
            req (dict): O dicionário de request traduzido.

        Returns:
            dict: Resposta de payload gerada para devolver ao cliente (com result ou error).
        """
        try:
            method_name = req.get('method')
            params = req.get('params', {})
            if method_name not in self.methods:
                return {"error": f"Metodo '{method_name}' inexistente no servidor."}

            # Executa o metodo dinamicamente passando os parâmetros mapeados
            return {"result": self.methods[method_name](**params)}

        except TypeError as e:
            return {"error": f"Parametros incorretos ou em falta para a operacao: {str(e)}"}
        except ValueError as e:
            # Captura erros de conversão de tipo (ex: passar texto onde se exigia um Inteiro)
            return {"error": f"Validacao de parametros: Tipo ou formato de valor invalido ({str(e)})."}
        except Exception as e:
            return {"error": f"Erro interno de processamento no servidor: {str(e)}"}

    def _handle_client(self, sock: socket.socket, addr: tuple) -> None:
        """
        Ouve ativamente as submissões de um cliente conetado de forma ininterrupta via keep-alive.

        Args:
            sock (socket.socket): O socket descritor.
            addr (tuple): Coordenadas da conexão IP.
        """
        print(f"[+] Cliente conectado: {addr}")
        try:
            buffer = ""
            while True:
                data = sock.recv(8192).decode('utf-8')
                if not data: break
                buffer += data

                while '\n' in buffer:
                    req_str, buffer = buffer.split('\n', 1)
                    if req_str.strip():
                        try:
                            resp = self._handle_request(json.loads(req_str))
                        except json.JSONDecodeError:
                            resp = {"error": "Formato JSON de comunicacao invalido."}
                        sock.send((json.dumps(resp) + '\n').encode('utf-8'))
        except Exception as e:
            print(f"[-] Erro com cliente {addr}: {e}")
        finally:
            sock.close()
            print(f"[-] Cliente desconectado: {addr}")

    def start(self) -> None:
        """Inicia e mantém ativo em background (thread) o servidor para escutar pedidos RPC TCP."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True
        print(f"Servidor RPC ativo na porta TCP {self.port}")

        try:
            while self.running:
                client_sock, client_addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\nA encerrar servidor com seguranca...")
        except OSError:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Comanda o graceful shutdown de todos os componentes do servidor, fechando a porta em uso."""
        self.running = False
        if self.server_socket:
            try: self.server_socket.close()
            except Exception: pass
        print("Servidor desligado.")

if __name__ == '__main__':
    RPCServer().start()