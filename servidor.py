import socket
import json
import threading
import inspect
import time
from primos import find_max_prime_parallel, is_prime, find_max_prime_sequential
from game_of_life import game_of_life_sequential, game_of_life_parallel

class RPCServer:
    def __init__(self, host='localhost', port=5000):
        self.host, self.port = host, port
        self.running = False
        self.server_socket = None

        self.methods = {
            'find_max_prime': self._find_max_prime,
            'is_prime': self._is_prime,
            'game_of_life': self._game_of_life,
            'list_methods': self._list_methods,
        }

    def _find_max_prime(self, timeout: float, workers: int = 1) -> dict:
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
        return is_prime(int(n))

    def _game_of_life(self, grid: list, generations: int, workers: int = 1) -> list:
        if workers > 1:
            return game_of_life_parallel(grid, int(generations), int(workers))
        return game_of_life_sequential(grid, int(generations))

    def _list_methods(self) -> list:
        lista = []
        for name, func in self.methods.items():
            sig = inspect.signature(func)
            params = [p for p in sig.parameters.keys() if p != 'self']
            desc = func.__doc__ if func.__doc__ else "Executa a operacao correspondente."
            lista.append({"nome": name, "parametros": params, "descricao": desc.strip()})
        return lista

    def _handle_request(self, req: dict) -> dict:
        try:
            method_name = req.get('method')
            params = req.get('params', {})
            if method_name not in self.methods:
                return {"error": f"Metodo {method_name} inexistente."}
            return {"result": self.methods[method_name](**params)}
        except TypeError as e:
            return {"error": f"Parametros incorretos: {str(e)}"}
        except Exception as e:
            return {"error": f"Erro interno do servidor: {str(e)}"}

    def _handle_client(self, sock: socket.socket, addr: tuple):
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
                            resp = {"error": "Formato JSON invalido."}
                        sock.send((json.dumps(resp) + '\n').encode('utf-8'))
        except Exception as e:
            print(f"[-] Erro com cliente {addr}: {e}")
        finally:
            sock.close()
            print(f"[-] Cliente desconectado: {addr}")

    def start(self):
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

    def stop(self):
        self.running = False
        if self.server_socket:
            try: self.server_socket.close()
            except Exception: pass
        print("Servidor desligado.")

if __name__ == '__main__':
    RPCServer().start()