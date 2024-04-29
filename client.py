import Pyro5.api


class RaftClient:
    def __init__(self):
        self.current_term = 1
        print("Cliente Raft inicializado e conectado ao servidor de nomes.")

    def find_leader(self):
        attempts = 0
        proxy = Pyro5.api.locate_ns()
        while attempts < 10:  # Define um número máximo de tentativas para evitar loop infinito
            leader_name = f"Líder_Termo{self.current_term}"
            try:
                leader_uri = proxy.lookup(leader_name)
                print(f"Encontrado líder para o termo {self.current_term}: {leader_uri}")
                return leader_uri
            except Pyro5.errors.NamingError:
                print(f"Líder para o termo {self.current_term} não encontrado.")
                self.current_term += 1  # Incrementa o termo e tenta novamente
                attempts += 1
        raise Exception("Líder não encontrado após várias tentativas.")

    def send_command(self, command):
        try:
            leader_uri = self.find_leader()
            leader = Pyro5.api.Proxy(leader_uri)
            result = leader.process_command(command)
            print(f"Resposta do líder: {result}")
        except Exception as e:
            print(f"Erro ao enviar comando ao líder: {e}")
            self.current_term += 1  # Incrementa o termo para tentar novamente
            print(f"Tentando novamente com termo {self.current_term}")
            self.send_command(command)

    def stop_leader(self):
        try:
            leader_uri = self.find_leader()
            leader = Pyro5.api.Proxy(leader_uri)
            leader.stop()
            print("Líder parado com sucesso.")
        except Exception as e:
            print(f"Erro ao parar líder: {e}")