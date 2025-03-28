import struct
import socket
import logging
import threading
import sys
import time
import math
from abc import ABC, abstractmethod


file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [stdout_handler]
# handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG, 
    format='[%(asctime)s] %(name)s - %(message)s',
    handlers=handlers
)

class RecvSendMsgsProtocol(ABC):
    MSG_SIZE = 16 # маленький размер
    
    @abstractmethod
    def recv(self, connected_socket):
        return ''
    
    @abstractmethod
    def send(self, connected_socket, text):
        pass

class Server:
    def __init__(self, protocol_handler, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.protocol_handler = protocol_handler
        self.logger = logging.getLogger('Server')
        
        
    def handle_client(self, client_socket):
        recv_text = self.protocol_handler.recv(client_socket)
        self.logger.info(f'recv "{recv_text}"')
        recv_text = self.protocol_handler.recv(client_socket)
        self.logger.info(f'recv "{recv_text}"')
        send_text = '?'*20
        self.protocol_handler.send(client_socket, send_text)
        self.logger.info(f'send "{send_text}"')
        recv_text = self.protocol_handler.recv(client_socket)
        self.logger.info(f'recv "{recv_text}"')
        send_text = '!'*20
        self.protocol_handler.send(client_socket, send_text)
        self.logger.info(f'send "{send_text}"')
        
    
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            self.logger.info(f'started on {(self.host, self.port)}')
            s.listen(1)
#             while True:
            client, addr = s.accept()
            with client:
                self.logger.info(f'connect {addr}')
                self.handle_client(client)

            self.logger.info(f'closed on {(self.host, self.port)}')

class Client:
    def __init__(self, protocol_handler, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.protocol_handler = protocol_handler
        self.logger = logging.getLogger('Client')
        
    
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            send_text = 'Hello '*5
            self.protocol_handler.send(s, send_text)
            self.logger.info(f'send "{send_text}"')
            send_text = 'World '*5
            self.protocol_handler.send(s, send_text)
            self.logger.info(f'send "{send_text}"')
            recv_text = self.protocol_handler.recv(s)
            self.logger.info(f'recv "{recv_text}"')
            send_text = 'Bye bye '*5
            self.protocol_handler.send(s, send_text)
            self.logger.info(f'send "{send_text}"')
            recv_text = self.protocol_handler.recv(s)
            self.logger.info(f'recv "{recv_text}"')