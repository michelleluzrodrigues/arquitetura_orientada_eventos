import Pyro5.api
import random
import threading
from enum import Enum


class ServerState(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3


@Pyro5.api.expose
class RaftServer:
    def __init__(self, server_id, peers, port):
        self.server_id = server_id # Identificador único do servidor
        self.state = ServerState.FOLLOWER # Estado inicial como FOLLOWER
        self.peers = peers # Lista de outros servidores (peers)
        self.port = port # Porta para comunicação
        self.current_term = 0 # Termo atual (ciclo de eleição)
        self.voted_for = None
        self.log = [] # Log de comandos
        self.last_command = None # Último comando processado
        # self.commit_index = 0
        # self.last_applied = 0
        self.leader_id = None # ID do líder atual
        proxy = Pyro5.api.locate_ns() # Localiza o serviço de nomes

        # Configuração do Pyro Daemon e registro no serviço de nomes
        self.daemon = Pyro5.api.Daemon(host="localhost", port=port)
        self.uri = self.daemon.register(self, objectId=f"server{server_id}")
        proxy.register(f"server{server_id}", self.uri)

        # Configuração de timers para eleição e heartbeat
        self.election_timeout = random.uniform(5, 10)
        self.heartbeat_interval = 2
        self.election_timer = threading.Timer(self.election_timeout, self.start_election)
        self.heartbeat_timer = threading.Timer(self.heartbeat_interval, self.send_heartbeat)

        self.running = True
        
    # método para verificar se o servidor está ativo.
    def ping(self):
        return True

    def start_election(self):
        if self.state != ServerState.LEADER:
            self.state = ServerState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.server_id
            vote_count = 1
            total_votes = 1

            print(f"Server {self.server_id} starting election while in term {self.current_term}...")

            for peer_uri in self.peers:
                try:
                    peer = Pyro5.api.Proxy(peer_uri)
                    if peer.request_vote(self.server_id, self.current_term):
                        vote_count += 1

                    total_votes += 1
                except Pyro5.errors.CommunicationError as e:
                    print(f"Failed to communicate with peer {peer_uri}: {e}")

            print(f"Server {self.server_id} received {vote_count} votes out of {total_votes}")
            if vote_count > total_votes // 2:
                self.state = ServerState.LEADER
                self.register_leader()
                print(f"Server {self.server_id} elected leader for term {self.current_term}")
                self.reset_heartbeat_timer()
                return

            self.reset_election_timer()

    # Registra o servidor como líder no serviço de nomes.
    def register_leader(self):
        # Atualiza ou registra o servidor como líder no serviço de nomes
        leader_name = f"Líder_Termo{self.current_term}"
        proxy = Pyro5.api.locate_ns()
        try:
            # Tenta remover um registro antigo se existir e registra o novo
            proxy.remove(leader_name)
        except Pyro5.errors.NamingError:
            pass  # Se o líder anterior não foi registrado, ignora o erro

        proxy.register(leader_name, self.uri)
        print(f"Registrado como {leader_name} no serviço de nomes")

    # Envia sinais de heartbeat aos pares para manter a autoridade como líder
    def send_heartbeat(self):
        if self.state == ServerState.LEADER:
            for peer_uri in self.peers:
                try:
                    peer = Pyro5.api.Proxy(peer_uri)
                    peer.request_hearbeat(self.server_id, self.current_term)
                except Pyro5.errors.CommunicationError as e:
                    print(f"Failed to communicate with peer {peer_uri}: {e}")
        self.reset_heartbeat_timer()

    #Recebe sinais de heartbeat de um líder e reseta o timer de eleição.
    def request_hearbeat(self, leader_id, term):
        if self.leader_id != leader_id:
            self.leader_id = leader_id
            self.voted_for = None
            self.state = ServerState.FOLLOWER
        self.reset_election_timer()

        if term >= self.current_term:
            self.current_term = term

    # Avalia uma solicitação de voto de outro servidor e decide se deve votar com base no termo e no log.
    def request_vote(self, candidate_id, term):
        if term > self.current_term and (self.voted_for is None or self.voted_for == candidate_id):
            self.voted_for = candidate_id
            self.current_term = term
            self.reset_election_timer()
            return True
        return False

    # Processa um comando se o servidor for o líder, tentando replicá-lo nos pares.
    def process_command(self, command):
        if self.state == ServerState.LEADER:
            print(f"Leader {self.server_id} received command: {command}")
            command_confirmation = 1
            total_servers = 1
            for peer_uri in self.peers:
                try:
                    peer = Pyro5.api.Proxy(peer_uri)
                    if peer.append_log(self.server_id, command):
                        command_confirmation += 1

                    total_servers += 1
                except Pyro5.errors.CommunicationError as e:
                    print(f"Failed to communicate with peer {peer_uri}: {e}")

            if command_confirmation > total_servers // 2:
                for peer_uri in self.peers:
                    try:
                        peer = Pyro5.api.Proxy(peer_uri)
                        peer.commit_log()
                    except Pyro5.errors.CommunicationError as e:
                        print(f"Failed to communicate with peer {peer_uri}: {e}")
                        
    # Adiciona um comando ao log se o comando for de um líder reconhecido.
    def append_log(self, leader_id, command):
        if leader_id == self.leader_id:
            self.last_command = command
            return True
        return False

    # Confirma os comandos no log local após a replicação bem-sucedida.
    def commit_log(self):
        if self.last_command is not None:
            self.log.append(self.last_command)
            self.last_command = None
            print(f"Server {self.server_id} log: {self.log}")

    # Reseta o timer de eleição para prevenir a ocorrência de eleições frequentes.
    def reset_election_timer(self):
        self.election_timer.cancel()
        self.election_timer = threading.Timer(random.uniform(5, 10), self.start_election)
        self.election_timer.start()

    # Reseta o timer de heartbeat para manter a regularidade dos envios.
    def reset_heartbeat_timer(self):
        self.heartbeat_timer.cancel()
        self.heartbeat_timer = threading.Timer(self.heartbeat_interval, self.send_heartbeat)
        self.heartbeat_timer.start()

    # nicia o loop principal do servidor, mantendo-o rodando.
    def run(self):
        self.election_timer.start()
        while self.running:
            self.daemon.requestLoop(lambda: self.running)

    # Para o servidor, cancelando timers e encerrando o daemon.
    def stop(self):
        self.running = False  # Seta o sinalizador para parar o loop e os timers
        self.election_timer.cancel()
        self.heartbeat_timer.cancel()
        self.daemon.shutdown()  # Encerra o daemon para liberar a porta e outros recursos
        print(f"Server {self.server_id} has been shut down.")
