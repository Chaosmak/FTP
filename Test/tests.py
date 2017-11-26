import os
import sys
import unittest
from unittest import mock
sys.path.append('..')
import FTPclient
import Input_handler as ih


def edit_msg(msg):
    return (msg + '\r\n').encode('utf-8')


@mock.patch('FTPclient.socket.socket', autospec=True)
class ClientTests(unittest.TestCase):
    def setUp(self):
        self.ftp = FTPclient.FTP()
        self.ftp.sock.close()
        self.without_args_func = {
            'CDUP': self.ftp.cdup,
            'PWD': self.ftp.pwd,
            'QUIT': self.ftp.quit,
            'ABOR': self.ftp.abor,
            'NOOP': self.ftp.noop}
        self.one_arg_functions = {
            'CWD': self.ftp.cwd,
            'DELE': self.ftp.dele,
            'MDTM': self.ftp.mdtm,
            'MKD': self.ftp.mkd,
            'RMD': self.ftp.rmd,
            'SITE': self.ftp.site,
            'SIZE': self.ftp.size,
            'TYPE': self.ftp.type}

    def test_connection(self, mock_sock):
        self.ftp.sock = mock_sock
        self.ftp.connect('1')
        mock_sock.connect.assert_called_with(('1', 21))

    def test_connection_with_username(self, mock_sock):
        self.ftp.sock = mock_sock
        self.ftp.connect('1', '2', '3')
        mock_sock.connect.assert_called_with(('1', 21))
        mock_sock.sendall.assert_called_with(edit_msg('USER 2'))

    def test_login(self, mock_sock):
        self.ftp.sock = mock_sock
        self.ftp.login('user', 'password')
        mock_sock.sendall.assert_called_with(edit_msg('USER user'))

    def test_0_arg_func(self, mock_sock):
        self.ftp.sock = mock_sock
        for k in self.without_args_func:
            self.without_args_func[k]()
            mock_sock.sendall.assert_called_with(edit_msg(k + ' '))

    def test_one_arg_commands(self, mock_sock):
        self.ftp.sock = mock_sock
        for k in self.one_arg_functions:
            self.one_arg_functions[k]('A')
            mock_sock.sendall.assert_called_with(edit_msg(k + ' A'))
            if k == 'CWD':
                self.one_arg_functions[k]('..')
                mock_sock.sendall.assert_called_with(b'CDUP \r\n')

    def test_rename(self, mock_sock):
        self.ftp.sock = mock_sock
        self.ftp.rename('1', '2')
        mock_sock.sendall.assert_called_with(edit_msg('RNTO 2'))

    def test_setmode(self, mock_sock):
        res = self.ftp.set_mode('PASV')
        self.assertEqual(res, 'Mode now is PASV')
        res = self.ftp.set_mode('1')
        self.assertEqual(res, 'Please set PASV or PORT')

    @mock.patch('FTPclient.Connection.upload_file', autospec=True)
    @mock.patch('FTPclient.parse_address', autospec=True)
    @mock.patch('FTPclient.FTP.send_command', autospec=True)
    @mock.patch('FTPclient.Connection.sock', autospec=True)
    def test_retr_stor(self, mock_sock, sender, parser, sock2, uploader):
        parser.return_value = ('100', '200')
        sender.return_value = 'Test'
        sock2.return_value = mock_sock
        self.ftp.sock = mock_sock
        file = open('file.txt', 'w+')
        res = self.ftp.retr('file.txt')
        self.assertEqual('Unable to connect. Server error \n' + 'Test', res)
        res = self.ftp.stor('file.txt')
        self.assertEqual('Unable to connect. Server error \n', res)
        file.close()
        os.remove('file.txt')

    @mock.patch('FTPclient.parse_address', autospec=True)
    @mock.patch('FTPclient.FTP.send_command', autospec=True)
    @mock.patch('FTPclient.Connection.sock', autospec=True)
    def test_list_nlst(self, mock_sock, sender, parser, sock2):
        parser.return_value = ('100', '200')
        sender.return_value = 'Test'
        sock2.return_value = mock_sock
        self.ftp.sock = mock_sock
        res = self.ftp.list()
        self.assertEqual('Unable to connect. Server error \n', res)
        res = self.ftp.nlst()
        self.assertEqual('Unable to connect. Server error \n', res)

    @mock.patch('FTPclient.Connection.get_port', autospec=True)
    @mock.patch('FTPclient.Connection.make_port', autospec=True)
    @mock.patch('FTPclient.parse_address', autospec=True)
    def test_make_port_ftp(self, parser, make_port, get_port, mock_sock):
        parser.return_value = ('100', '200')
        make_port.return_value = ('127.0.0.1', 8080)
        get_port.return_value = '8080'
        mock_sock.return_value = mock_sock
        self.ftp.sock = mock_sock
        res = 'Error: ' + 'Unable to connect. Server error \n' +\
              '\nPort closed. Passive mode is on'
        self.assertEqual(res, self.ftp.makeport()[0])

    @mock.patch('FTPclient.Connection.create_pasv_connection', autospec=True)
    def test_download(self, pasv, mock_sock):
        pasv.return_value = '2'
        mock_sock.settimeout.return_value = '100'
        mock_sock.recv.return_value = ''
        connection = FTPclient.Connection()
        connection.sock = mock_sock
        self.assertEqual(connection.download_file('file.txt'),
                         'File was downloaded')
        os.remove('file.txt')

    @mock.patch('FTPclient.Connection.create_pasv_connection', autospec=True)
    def test_upload(self, pasv, mock_sock):
        pasv.return_value = '2'
        mock_sock.settimeout.return_value = '100'
        mock_sock.recv.return_value = ''
        connection = FTPclient.Connection()
        connection.sock = mock_sock
        file = open('file.txt', 'w+')
        self.assertEqual(connection.upload_file('file.txt'),
                         'File uploaded')
        file.close()
        os.remove('file.txt')

    @mock.patch('FTPclient.Connection.create_pasv_connection', autospec=True)
    def test_make_port_conn(self, pasv, mock_sock):
        self.ftp.sock = mock_sock
        pasv.return_value = '2'
        mock_sock.settimeout.return_value = '100'
        mock_sock.recv.return_value = ''
        mock_sock.getsockname.return_value = (1, 2)
        connection = FTPclient.Connection()
        connection.sock = mock_sock
        self.assertEqual(len(connection.make_port(mock_sock)), 2)

    def test_adr_parser(self, mock_sock):
        self.assertEqual(FTPclient.parse_address('192,168,0,1,21,216'),
                         ('192.168.0.1', 5592))


# @mock.patch('Input_handler.input')
# @mock.patch('Input_handler.print_result')
# @mock.patch('Input_handler.print_help')
class HandlerTests(unittest.TestCase):
    def test_settings_parser(self):
        file = open('settings.txt', 'w+')
        file.write('1=1\n2=2\n3=3')
        file.close()
        res = ih.get_settings('settings.txt')
        self.assertEqual(res, ['1', '2', '3'])

    @mock.patch('Input_handler.input')
    @mock.patch('Input_handler.print_result')
    @mock.patch('Input_handler.create_receiver')
    def test_console_starter(self, receiver, pr, new_input):
        new_input.return_value = 'exit'
        ih.start_console_ftp()
        new_input.assert_called_with(ih.MSG_WITHOUT_SETTINGS)
        pr.assert_called_with('Goodbye')
        new_input.return_value = 'fortest'
        receiver.return_value = 'quit'
        ih.start_console_ftp(1)
        new_input.assert_called()
        receiver.asser_called_with('host', 1)

    @mock.patch('Input_handler.input')
    @mock.patch('Input_handler.print_result')
    @mock.patch('Input_handler.FTPclient')
    @mock.patch('Input_handler.receive_command')
    def test_receiver_creator(self, rec_cmd, ftp, pr, new_input):
        ftp.FTP.return_value = ftp
        ftp.login.return_value = 'login'
        rec_cmd.return_value = 'QUIT'
        res = ih.create_receiver('host')
        ftp.login.assert_called()
        pr.assert_called_with('login')
        self.assertEqual(res, 'QUIT')
        ftp.login.return_value = '4'
        ih.create_receiver('host', [1, 2, 3])
        pr.assert_called_with('4')

    @mock.patch('Input_handler.FTPclient')
    @mock.patch('Input_handler.command_handler')
    @mock.patch('Input_handler.get_cmd')
    def test_command_receiver(self, cmd, handler, ftp):
        cmd.return_value = ['QUIT']
        handler.return_value = 'QUIT'
        res = ih.receive_command(ftp)
        self.assertEqual(res, 'QUIT')

    @mock.patch('Input_handler.input')
    @mock.patch('Input_handler.print_result')
    @mock.patch('Input_handler.FTPclient')
    def test_cmd_handler(self, ftp, pr, new_input):
        ftp.send_command.return_value = '1'
        ih.command_handler(None, 'send 123', ftp)
        pr.assert_called_with('1')
        ih.command_handler(None, (2, 3), ftp)
        pr.assert_called_with('Wrong input.')
        self.assertEqual(ih.command_handler({'QUIT': pr}, ['QUIT'], ftp),
                         'QUIT')
        new_input.return_value = 2
        ih.command_handler({'1': new_input}, ['1', '2'], ftp)
        pr.assert_called_with(2)
        ih.command_handler({'1': new_input}, ['1', '2', '3'], ftp)
        pr.assert_called_with(2)
        ih.command_handler({'1': new_input}, ['test', '2', '3'], ftp)
        pr.assert_called_with('Unknown command. Use \"Help\".')


    @mock.patch('Input_handler.print_result')
    @mock.patch('Input_handler.input')
    def test_get_cmd(self, new_input, pr):
        new_input.return_value = 'send'
        self.assertEqual(ih.get_cmd('test'), 'send')
        new_input.return_value = 'RENAME BEST#_#FILE OF_WORLD'
        self.assertEqual(ih.get_cmd('test'),
                         ['RENAME', 'BEST FILE', 'OF_WORLD'])
        new_input.return_value = 'a b c d'
        ih.get_cmd('test')
        pr.assert_called_with("Something wrong. Try again")

    def test_parser(self):
        parser = ih.parse_args(['-s', '1.txt'])
        self.assertEqual(1, len(parser.stor))
        parser = ih.parse_args(['-r', '1.txt'])
        self.assertEqual(1, len(parser.retr))

    @mock.patch('Input_handler.FTPclient')
    @mock.patch('Input_handler.parse_args')
    def test_main(self, parser, ftp):
        parser.return_value = parser
        parser.stor.return_value = 'stor'
        ftp.FTP.return_value = ftp
        ih.main()
        ftp.stor.assert_called()


unittest.main()