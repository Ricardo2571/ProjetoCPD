import socket
import json
import threading
import inspect
from primos import find_max_prime_parallel, is_prime
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
        """Encontra o primo e retorna estatísticas de execução."""
        p, t_found, t_total = find_max_prime_parallel(timeout, max(1, workers), True)

        return {
            "max_prime": p,
            "time_found": round(t_found, 4),
            "total_time": round(t_total, 4)
        }

    def _is_prime(self, n: int) -> bool:
        return is_prime(n)

    def _game_of_life(self, grid: list, generations: int, workers: int = 1) -> list:
        if workers > 1: return game_of_life_parallel(grid, generations, workers)
        return game_of_life_sequential(grid, generations)

    def _list_methods(self) -> list:
        """Usa reflexão para listar os métodos disponíveis."""
        lista = []
        for name, func in self.methods.items():
            sig = inspect.signature(func)
            # Remove 'self' param se existir
            params = [p for p in sig.parameters.keys() if p != 'self']
            desc = func.__doc__ if func.__doc__ else "Executa operação."
            lista.append({"nome": name, "parametros": params, "descricao": desc})
        return lista

    def _handle_request(self, req: dict) -> dict:
        try:
            method_name = req.get('method')
            params = req.get('params', {})

            if method_name not in self.methods:
                return {"error": f"Metodo {method_name} inexistente."}

            result = self.methods[method_name](**params)
            return {"result": result}
        except TypeError as e:
            return {"error": f"Parametros invalidos: {str(e)}"}
        except Exception as e:
            return {"error": f"Erro interno: {str(e)}"}

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
                            req_json = json.loads(req_str)
                            resp_json = self._handle_request(req_json)
                        except json.JSONDecodeError:
                            resp_json = {"error": "Formato JSON invalido."}

                        sock.send((json.dumps(resp_json) + '\n').encode('utf-8'))
        except Exception as e:
            print(f"[-] Erro cliente {addr}: {e}")
        finally:
            sock.close()
            print(f"[-] Cliente desconectado: {addr}")

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)  # Permite múltiplos clientes concorrentes
        self.running = True
        print(f"Servidor RPC a escutar em {self.host}:{self.port}")

        try:
            while self.running:
                client_sock, client_addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\nA encerrar servidor...")
        except OSError:
            # Ignora o erro gerado quando o socket é fechado pelo método stop()
            pass
        finally:
            self.stop()

    def stop(self):
        """Para o servidor RPC e fecha as ligações."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        print("Servidor RPC parado.")


if __name__ == '__main__':
    server = RPCServer()
    server.start()
