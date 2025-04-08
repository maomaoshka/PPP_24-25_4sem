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

HOST = 'localhost'
PORT = 12345

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
        # recv_text = self.protocol_handler.recv(client_socket)
        # self.logger.info(f'recv "{recv_text}"')
        # send_text = '?'*20
        # self.protocol_handler.send(client_socket, send_text)
        # self.logger.info(f'send "{send_text}"')
        # recv_text = self.protocol_handler.recv(client_socket)
        # self.logger.info(f'recv "{recv_text}"')
        # send_text = '!'*20
        # self.protocol_handler.send(client_socket, send_text)
        # self.logger.info(f'send "{send_text}"')


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
            # send_text = 'World '*5
            # self.protocol_handler.send(s, send_text)
            # self.logger.info(f'send "{send_text}"')
            # recv_text = self.protocol_handler.recv(s)
            # self.logger.info(f'recv "{recv_text}"')
            # send_text = 'Bye bye '*5
            # self.protocol_handler.send(s, send_text)
            # self.logger.info(f'send "{send_text}"')
            # recv_text = self.protocol_handler.recv(s)
            # self.logger.info(f'recv "{recv_text}"')

class SizeProtocol(RecvSendMsgsProtocol):
    def recv(self, connected_socket):
        data = connected_socket.recv(struct.calcsize('I')) # читаем данный размера int
        size, = struct.unpack('I', data) # читаем ожидаемый размер посылки
        res_data = b''
        while len(res_data) < size: # пока то, что мы прочитали меньше ожидаемого - читаем дальше
            data = connected_socket.recv(min(self.MSG_SIZE, size-len(res_data))) # а если две посылки слипнутся? надо читать только свое, отсюда min
            res_data += data
        return res_data.decode()


    def send(self, connected_socket, text):
        connected_socket.send(struct.pack('I', len(text))) # пакуем и отправляем размер
        connected_socket.sendall(text.encode()) # отпраляем остальное

# class NumberProtocol(RecvSendMsgsProtocol):
#     DATA_SIZE = SizeProtocol.MSG_SIZE - struct.calcsize('II') # мы заранее посчитаем сколько отводится под данные
#     DATA_TEMPLATE = f'II{DATA_SIZE}s' # Соберем шаблон, чтоб каждый раз так не делать

#     def recv(self, connected_socket):
#         data = connected_socket.recv(self.MSG_SIZE) # Читаем данные
#         number, last, msg = struct.unpack(self.DATA_TEMPLATE, data) # распаковываем по шаблону
#         res_data = msg
#         while number < last: # пока пакет не последний мы читаем
#             data = connected_socket.recv(self.MSG_SIZE)
#             number, last, msg = struct.unpack(self.DATA_TEMPLATE, data)
#             res_data += msg
#         return res_data.decode()


#     def send(self, connected_socket, text):
#         last_number = math.ceil(len(text) / self.DATA_SIZE) - 1 # Считаем последний пакет
#         for i in range(0, len(text), self.DATA_SIZE): # Делаем срезы данных
#             chunck = text[i:i+self.DATA_SIZE] # Вот и срез
#             number = i // self.DATA_SIZE # Номер текущего пакета
#             connected_socket.send(struct.pack(self.DATA_TEMPLATE, number, last_number, chunck.encode())) # сборка и отправка

# class BlockingProtocol(RecvSendMsgsProtocol):
#     def recv(self, connected_socket):
#         res_data = b''
#         data = connected_socket.recv(self.MSG_SIZE) # С блокировкой ждем начала сообщения
#         connected_socket.setblocking(False) # Снимаем блокировку
#         while data:
#             res_data += data
#             try: # Если мы пытаемся читать, а там пусто, то падает ошибка. Считаем, что сообщение закончилось
#                 data = connected_socket.recv(self.MSG_SIZE)
#             except:
#                 break
#         connected_socket.setblocking(True) # Ставим ее обратно
#         connected_socket.send(b'ok')
#         return res_data.decode()


#     def send(self, connected_socket, text):
#         connected_socket.sendall(text.encode()) # просто отправляем все, что есть
#         response = connected_socket.recv(self.MSG_SIZE).decode() # ответ, что сообщение принято
#         if response != 'ok': # если в ответе все плохо, то все плохо, что еще поделать то?
#             pass

def test(protocol_cls):
    server = Server(protocol_cls())
    client = Client(protocol_cls())

    t_s = threading.Thread(target=Server.run, args=[server]) # Почему так? Потому что self - это на самом деле первый аргумент
    t_c = threading.Thread(target=client.run, args=[]) # А это второй вариант той же записи
    t_s.start()
    time.sleep(1) # Чтоб сервер успел запуститься
    t_c.start()
    t_c.join() # Ждем завершения потоков
    t_s.join()

test(SizeProtocol)
# test(NumberProtocol)
# test(BlockingProtocol)

