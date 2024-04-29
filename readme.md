# Sistema de Servidores com Raft e Pyro5
Este projeto implementa um sistema de servidores distribuídos usando o módulo Pyro5 em Python, com a aplicação do algoritmo de Raft para eleição de um líder entre os servidores. O líder registrado no servidor de nomes do Pyro5 coordena a adição de registros nos logs de todos os servidores, garantindo consistência e recuperação de falhas, incluindo a reeleição de um novo líder se necessário.

## Requisitos
- Python 3.10
- Pyro5
- Um ambiente que permita múltiplas execuções de terminal para o servidor de nomes, servidores e cliente.


## Configuração do Ambiente
Para instalar as dependências necessárias, execute o seguinte comando:

```bash
pip install Pyro5
```

## Inicialização do Projeto
Iniciar o Servidor de Nomes
Abra um terminal e execute o servidor de nomes Pyro5:


```bash
python -m Pyro5.nameserver
```

## Iniciar os Servidores
Em um novo terminal, navegue até o diretório do projeto e execute o seguinte comando para iniciar os servidores:

```bash
python main.py
```

Este script inicializará quatro servidores que participarão na eleição de um líder usando o algoritmo de Raft.  
Neste terminal sera exibidos os logs de execução dos servidores.

## Cliente
O cliente pode ser executado interativamente para testar a funcionalidade do sistema. Para isso, você pode usar um terminal interativo de Python:

```bash
python
```

Dentro do ambiente interativo, você pode criar uma instância do cliente e usar os métodos para enviar comandos ou simular falhas:

```python
from client import RaftClient

# Cria uma instância do cliente
cliente = RaftClient()

# Envia um comando para adicionar um registro no log
cliente.send_command("Nova entrada de log")

# Simula a falha do líder
cliente.stop_leader()
```

## Funcionamento do Sistema
- Os servidores utilizam o algoritmo de Raft para eleger um líder.
- O líder se registra como Leader_TermoX no servidor de nomes do Pyro.
- O cliente procura o líder e envia comandos para adicionar registros.
- O líder propaga o comando para os outros servidores.
- Se o líder falhar, os servidores restantes realizarão uma nova eleição.