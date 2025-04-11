import struct
import socket
import logging
import threading
import sys
import time
import math
from abc import ABC, abstractmethod
import os
import json


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
        self.commands ={'make_me_a_tree': self.build_path_tree(),
                        'get_env': self.give_env()}

# def update_environment(self):
#     """Обновляет информацию о программах и окружении"""
#     return self.build_path_tree()

    def give_env(self):
        return dict(os.environ)

    def set_env(self,var,val):
        os.environ[var] = val
        ans =f"{var} variable is now set to {val}"
        #print(ans)
        return ans

    def handle_client(self, client_socket):
        recv_text = self.protocol_handler.recv(client_socket)
        self.logger.info(f'recv "{recv_text}"')
        if recv_text[:7]=='set_env':
            var =recv_text.split(' ')[1]
            val =recv_text.split(' ')[2]
            res =self.set_env(var,val)
            #print(res)
        elif recv_text in self.commands.keys():
            self.commands[recv_text]

            res =self.commands[recv_text]

        #print(f"Отправляемая строка: {res}") 
        print(f"Отправлено {len(res)} байт")
        self.protocol_handler.send(client_socket, json.dumps(res, indent=2, ensure_ascii=False))
        self.logger.info(f'sent result')


    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, self.port))
                self.logger.info(f'started on {(self.host, self.port)}')
                s.listen(1)
                #while True:
                client, addr = s.accept()
                with client:
                    self.logger.info(f'connect {addr}')
                    self.handle_client(client)

        finally:
            time.sleep(0.5)
            s.close()
            self.logger.info("Server stopped")
            self.logger.info(f'closed on {(self.host, self.port)}')

    def is_executable(self, file_path):
    # Проверяет, является ли файл исполняемым (есть ли у него право на исполнения, exe и т.д)
    # От разные системы по разному понимают исполняемые файлы, поэтому есть разделение на linux и windows
        if os.name == 'posix':  # Unix-системы (Linux, macOS)
            return os.access(file_path, os.X_OK)
        else:  # Windows
            return file_path.lower().endswith(('.exe', '.bat', '.cmd', '.ps1'))

    def build_path_tree(self):
        # Возвращает список всех исполняемых файлов в PATH.
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        tree = {}

        for dir_path in path_dirs:
            # Пропускаем несуществующие директории
            if not os.path.isdir(dir_path):
                continue
            # Разбиваем путь на части os.sep = '/'
            parts = [p for p in dir_path.split(os.sep) if p]
            # Корень дерева
            current_level = tree
            # Строим ветви для каждой папки (кроме последнего)
            for part in parts[:-2]:
                # Если папки нет, то создаем новую ветку
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

            # Последняя часть это самая глубокая папка с исполняемыми файлами
            last_dir = parts[-1]

            # # Добавляем её в дерево
            current_level[last_dir] = []

            # Добавляем исполняемые файлы из этой папки
            try:
                for file_name in os.listdir(dir_path):
                    full_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(full_path) and self.is_executable(full_path):
                        current_level[last_dir].append(file_name)
            except:
                # Пропускаем папки без доступа
                continue

        with open(f"{os.path.abspath(__file__)[:-7]}\\ans_server.json", "w+") as f:
            f.write(json.dumps(tree, indent=2, ensure_ascii=False))
        
        return tree
        
class Client:
    def __init__(self, protocol_handler, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.protocol_handler = protocol_handler
        self.logger = logging.getLogger('Client')

    def run(self):
        try:
            print("1. Получить дерево файлов\n2. Получить переменные окружения\n3. Установить переменную")
            choice = input("Выбор: ")

            if choice=='1':
                send_text = 'make_me_a_tree'
            elif choice=='2':
                send_text ='get_env'
            elif  choice=='3':
                var = input("Имя переменной: ")
                value = input("Значение: ")
                send_text =f'set_env {var} {value}'

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                self.protocol_handler.send(s, send_text)
                self.logger.info(f'send "{send_text}"')

                recv_text = self.protocol_handler.recv(s)
                print(f"Получено {len(recv_text)} байт")
                print(recv_text)
                self.logger.info(f'recv ans')
            
            # Сохраняем в файл
            if choice=='1':
                with open(f"{os.path.abspath(__file__)[:-7]}\\ans_client.json", "w+") as f:
                    f.write(recv_text)
            else:
                print(recv_text)
            
            self.logger.info(f'done!')

        finally:
            s.close()
            self.logger.info("Client stopped")

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


def main():
    test(SizeProtocol)

if __name__ == "__main__":
    main()