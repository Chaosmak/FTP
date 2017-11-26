import socket
import re
import os
import time

CRLF = '\r\n'
TIMED_OUT = "Timed out. Unable to connect."
SERVER_ERROR = 'Unable to connect. Server error \n'
DOWNLOAD_PROBLEM = "Timed out download. Unable to connect."


def print_response(msg):
    print(msg + '\n')


class FTP:
    connection_type = 'PASV'

    def __init__(self, host='', user='',
                 password='', port=21):
        self.port = port
        self.host = host
        self.sock = socket.socket()
        if host != '':
            self.connect(host, user, password)

    def connect(self, host, user='', password=''):
        """Connect to server"""
        if host:
            self.host = host
        self.sock.connect((self.host, self.port))
        response = self.get_resp()
        if user != '' and password != '':
            result = self.login(user, password)
            return result
        else:
            return response

    def login(self, user, password):
        """Login to server"""
        response = self.send_command('USER ' + user)
        if response[0] == '3':
            response = self.send_command('PASS ' + password)
        return response

    def dele(self, name):
        """Delete file"""
        return self.normal_sender('DELE', name, ['250'])

    def mkd(self, name):
        """Make directory"""
        return self.normal_sender('MKD', name, ['257'])

    def rmd(self, name):
        """Remove directory"""
        return self.normal_sender('RMD', name, ['250'])

    def cdup(self):
        return self.normal_sender('CDUP', '', 'all')

    def cwd(self, name):
        """Change to a dir"""
        if name == '..':
            return self.cdup()
        return self.normal_sender('CWD', name, ['250'])

    def pwd(self):
        """Current directory"""
        return self.normal_sender('PWD', '', ['257'])

    def abor(self):
        """Abort file transfer (probably does not work)"""
        return self.normal_sender('ABOR', '', ['426', '225', '226'])

    def rename(self, old_name, new_name):
        self.normal_sender('RNFR', old_name, ['350'])
        return self.normal_sender('RNTO', new_name, ['250'])

    def mdtm(self, name):
        return self.normal_sender('MDTM', name, 'all')

    def site(self, command):
        return self.normal_sender('SITE', command, '214')

    def size(self, filename):
        """Size in bytes"""
        return self.normal_sender('SIZE', filename, '213')

    def type(self, command):
        """
        Sets the type of file to be transferred. type-character can be any of:
            A - ASCII text
            E - EBCDIC text
            I - image (binary data)
            L - local format
        """
        if command not in {'A', 'E', 'I', 'L'}:
            return 'Wrong command'
        else:
            return self.normal_sender('TYPE', command, '200')

    def set_mode(self, mode):
        if mode == 'PASV' or mode == 'PORT':
            self.connection_type = mode
            return 'Mode now is ' + mode
        return 'Please set PASV or PORT'

    def get_connection(self):
        if self.connection_type == 'PASV':
            return self.pasv()
        elif self.connection_type == 'PORT':
            return self.makeport()

    def noop(self):
        return self.normal_sender('NOOP', '', 'all')

    def list(self, name=None):
        resp, connection = self.get_connection()
        if name:
            cmd = 'LIST ' + name
        else:
            cmd = 'LIST'
        self.send_command(cmd)
        resp1 = self.get_resp()
        if self.connection_type == 'PORT':
            conn, addr = connection.sock.accept()
            connection.sock = conn
        resp2 = connection.get_resp()
        resp3 = self.get_resp()
        return resp2

    def nlst(self):
        resp, connection = self.get_connection()
        resp1 = self.send_command('NLST')
        if self.connection_type == 'PORT':
            conn, addr = connection.sock.accept()
            connection.sock = conn
        resp2 = connection.get_resp()
        resp3 = self.get_resp()
        return resp2

    def retr(self, name, path=None):
        """Download file"""
        resp, connection = self.get_connection()
        filename = os.path.basename(name)
        size = self.size(filename).split(' ')[1]
        resp1 = self.send_command('RETR ' + name)
        if self.connection_type == 'PORT':
            conn, addr = connection.sock.accept()
            connection.sock = conn
        if resp1[:3] == '150' or resp1[:3] == '226':
            resp2 = connection.download_file(filename, int(size), path)
        else:
            return SERVER_ERROR + resp1
        resp3 = self.get_resp()
        return resp3

    def retr_folder(self, folder_name, path=None):
        """Download folder"""
        current_folder = self.pwd().split('"')[1]
        cwd_resp = self.cwd(folder_name)
        if not cwd_resp.startswith('2'):
            return 'Wrong folder name'
        line_list = [x.split() for x in self.list().split('\r\n')]
        if not path:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder_name)
        else:
            path = os.path.join(path, folder_name)
        for line in line_list:
            if len(line) < 8:
                continue
            name = ' '.join(line[8:])
            if line[0].startswith('dr'):
                self.retr_folder(name, path)
            else:
                self.retr(name, path)
        self.cwd(current_folder)
        return 'Folder downloaded'

    def stor(self, path):
        if not os.path.isfile(path):
            return 'Wrong path'
        resp, connection = self.get_connection()
        filename = os.path.basename(path)
        resp1 = self.send_command('STOR ' + filename)
        if self.connection_type == 'PORT':
            conn, addr = connection.sock.accept()
            connection.sock = conn
        if resp1:
            resp2 = connection.upload_file(path)
        else:
            return SERVER_ERROR
        time.sleep(1)
        resp3 = self.get_resp()
        return resp3

    def pasv(self):
        """
        Создаем пассивное соединение для приема/передачи данных.
        """
        self.connection_type = 'PASV'
        resp = self.send_command('PASV')
        host, port = parse_address(resp)
        connection = Connection(host, port, 'PASV')
        return resp, connection

    def makeport(self):
        """Соединение для передачи данных на порт клиента"""
        connection = Connection(connection_type='PORT', sock=self.sock)
        address = connection.get_port()
        resp = self.normal_sender('PORT', address, '200')
        if resp[:3] != '200':
            return resp + '\nPort closed. Passive mode is on', self.pasv()[1]
        return resp + '\n Active mode is on', connection

    def send_command(self, msg):
        """Send command to server"""
        msg += CRLF
        self.sock.sendall(msg.encode('utf-8'))
        return self.get_resp()

    def get_resp(self):
        return recv_all(self.sock)

    def normal_sender(self, command, message, codes):
        response = self.send_command(command + ' ' + message)
        if response[:3] not in codes and codes != 'all':
            return "Error: " + response
        return response

    def quit(self):
        """Exit the server and close socket"""
        response = self.send_command('QUIT ')
        self.close()
        return response

    def close(self):
        """Close the socket"""
        if self.sock is not None:
            self.sock.close()


class Connection:
    sock = None
    _port = None

    def __init__(self, host=None, port=None,
                 connection_type='PASV', sock=None):
        if connection_type == 'PASV':
            self.create_pasv_connection(host, port)
        if connection_type == 'PORT':
            self.create_port_connection(sock)

    def create_pasv_connection(self, host, port):
        self.sock = socket.socket()
        self.sock.connect((host, port))

    def get_port(self):
        return self._port

    def create_port_connection(self, sock):
        res = self.make_port(sock)
        host, port = res
        host = host.split('.')
        port = [repr(port // 256), repr(port % 256)]
        result = host + port
        self._port = ','.join(result)

    def make_port(self, old_sock):
        new_sock = None
        for res in socket.getaddrinfo(None, 0,
                                      socket.AF_INET,
                                      socket.SOCK_STREAM,
                                      0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                new_sock = socket.socket(af, socktype, proto)
                new_sock.bind(sa)
                new_sock.listen(1)
            except OSError as msg:
                if new_sock:
                    new_sock.close()
                new_sock = None
                continue
            break
        host = old_sock.getsockname()[0]
        port = new_sock.getsockname()[1]
        self.sock = new_sock
        return host, port

    def print_stat(self, total_time, size):
        print('Загружено за ' + str(total_time) + ' секунд.')
        print('Средня скорость ' + str(size / (total_time * 1024)) + ' kb/s')

    def get_stats(self, start_time, iteration, chunk_size, x, len_part, speed):
        iteration += len_part
        delta = time.time() - start_time
        if delta > 1:
            speed = (chunk_size * x) // (delta * 1024)
            start_time = time.time()
            x = 0
        return iteration, speed, start_time, x, delta

    def download_file(self, filename, size, folder=None):
        chunk_size = 4096
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if folder:
            if not os.path.exists(folder):
                os.makedirs(folder)
        else:
            folder = current_dir
        filename = os.path.join(folder, filename)
        f = open(filename, 'wb')
        result = None
        temp_start = start = time.time()
        speed = x = iteration = 0
        while True:
            x += 1
            self.sock.settimeout(10.0)
            try:
                part = self.sock.recv(chunk_size)
                time.sleep(0.00001)  # Без этого передача может прерваться
                if not part:
                    break
                iteration, speed, temp_start, x, delta = self.get_stats(
                    temp_start, iteration, chunk_size, x, len(part), speed)
                self.print_progress_bar(iteration, size, speed=speed)
            except TimeoutError:
                result = DOWNLOAD_PROBLEM
                break
            f.write(part)
        f.close()
        self.sock.close()
        self.print_stat(time.time() - start, size)
        if result is None:
            result = 'File was downloaded'
        return result

    def upload_file(self, file):
        size = os.stat(file).st_size
        f = open(file, 'rb')
        chunk_size = 2048
        temp_start = start = time.time()
        speed = x = iteration = 0
        while 1:
            x += 1
            buf = f.read(chunk_size)
            if not buf:
                break
            time.sleep(0.00001)  # Без этого передача может прерваться
            self.sock.sendall(buf)
            iteration, speed, temp_start, x, delta = self.get_stats(
                temp_start, iteration, chunk_size, x, len(buf), speed)
            self.print_progress_bar(iteration, size, speed=speed)
        self.sock.close()
        f.close()
        self.print_stat(time.time() - start, size)
        return 'File uploaded'

    def print_progress_bar(self, iteration, total, speed=None, prefix='',
                           suffix='', decimals=1, length=100, fill='█'):
        percent = ("{0:." + str(decimals) + "f}").format(
            100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
        if filled_length > total:
            filled_length = total
        bar = fill * filled_length + '-' * (length - filled_length)
        print('\r{} |{}| {}% {} {} kb/s'.format(
            prefix, bar, percent, suffix, speed), end='\r')
        if iteration == total:
            print()

    def get_resp(self):
        response = recv_all(self.sock)
        self.sock.close()
        return response


def parse_address(msg):
    numbers = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', msg).groups()
    host = '.'.join(numbers[:4])
    port = (int(numbers[4]) * 256) + int(numbers[5])
    return host, port


def recv_all(sock):
    try:
        size = 4096
        data = []
        while True:
            sock.settimeout(5.0)
            try:
                part = sock.recv(size)
            except:
                return TIMED_OUT
            data.append(part.decode("utf-8"))
            if len(part) < size:
                break
        return ''.join(data)
    except:
        return SERVER_ERROR
