import Pyro5.api
import threading
import time
import signal
from server import RaftServer
from client import RaftClient


def check_servers_ready(servers):
    for server_uri in servers:
        try:
            server = Pyro5.api.Proxy(server_uri)
            server.ping()
        except Pyro5.errors.CommunicationError as e:
            print(f"Failed to connect to server {server_uri}: {e}")
            return False
    return True


def start_elections(servers):
    if check_servers_ready(servers):
        for server_uri in servers:
            server = Pyro5.api.Proxy(server_uri)
            server.start_election()
        print("Election timers started on all servers.")
    else:
        print("Waiting for all servers to be ready...")
        threading.Timer(5, start_elections, [servers]).start()


def main():
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        print("Signal received, shutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    peers = [f"PYRO:server{i + 1}@localhost:{5501 + i}" for i in range(4)]
    servers = []
    threads = []

    for i, peer in enumerate(peers):
        try:
            current_peers = peers[:]
            # Remove o endereço do servidor atual da lista de peers
            current_peers.remove(peer)

            server = RaftServer(i + 1, current_peers, 5501 + i)
            servers.append(peer)
            t = threading.Thread(target=server.run)
            t.daemon = True
            t.start()
            threads.append(t)
            print(f"Server thread {i + 1} started.")
            time.sleep(1)  # Delays for stability
        except Exception as e:
            print(f"Error starting server {i + 1}: {e}")

    while running:
        time.sleep(1)  # Pausa entre ciclos para evitar uso excessivo de CPU

    print("Shutting down...")
    # Limpeza e encerramento de threads
    for t in threads:
        t.join()

    try:
        client = RaftClient()
        client.send_command("Add data to log")
    except Exception as e:
        print(f"Error initializing Raft client: {e}")


main()
