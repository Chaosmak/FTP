import FTPclient
import os
import argparse
import sys

__version__ = '0.1'
__author__ = 'Mokeev Maxim'
__email__ = 'chaosmak789@gmail.com'

MSG_WITH_SETTINGS = "Enter 'help' for help or 'exit' for exit\nPress 'Enter' for connect\n"
MSG_WITHOUT_SETTINGS = "Hostname or quit command: "


def get_cmd(msg):
    result = input(msg)
    if result.lower().startswith('send'):
        return result
    res = result.split(' ')
    result = [part.replace('#_#', ' ') for part in res]
    if len(result) not in {1, 2, 3}:
        print_result("Something wrong. Try again")
        return None
    return result


def print_result(result):
    """Вдруг в будущем понадобиться выводить по-другому"""
    print('\n' + str(result))


class Command:
    FTP = FTPclient.FTP()

    def __init__(self, ftp=None):
        if ftp:
            self.FTP = ftp
        else:
            self.FTP = FTPclient.FTP()

    def get_cmd(self):
        ftp = self.FTP
        return {
            'RETRFOLD': {'func': ftp.retr_folder, 'help': 'retrieve a remove folder'},
            'LIST': {'func': ftp.list, 'help': 'list remote files'},
            'CWD': {'func': ftp.cwd, 'help': 'change working directory'},
            'CDUP': {'func': ftp.cdup, 'help': 'CWD to the parent of the current directory'},
            'DELE': {'func': ftp.dele, 'help': 'delete a remote file'},
            'MDTM': {'func': ftp.mdtm, 'help': 'return the modification time of a file'},
            'MKD': {'func': ftp.mkd, 'help': 'make a remote directory'},
            'NLST': {'func': ftp.nlst, 'help': 'name list of remote directory'},
            'PWD': {'func': ftp.pwd, 'help': 'print working directory'},
            'QUIT': {'func': ftp.quit, 'help': 'terminate the connection'},
            'RETR': {'func': ftp.retr, 'help': 'retrieve a remote file'},
            'RMD': {'func': ftp.rmd, 'help': 'remove a remote directory'},
            'RENAME': {'func': ftp.rename, 'help': 'rename old_filename new_filename - rename file or folder'},
            'SITE': {'func': ftp.site, 'help': 'site-specific commands'},
            'SIZE': {'func': ftp.size, 'help': 'return the size of a file'},
            'STOR': {'func': ftp.stor, 'help': 'store a file on the remote host'},
            'TYPE': {'func': ftp.type, 'help': 'set transfer type'},
            'SETMODE': {'func': ftp.set_mode, 'help': 'SETMODE PASV/PORT - enter passive or active (port) mode'},
            'NOOP': {'func': ftp.noop, 'help': 'do nothing'},
        }

    def get_help(self):
        notice = 'In the names of folders or files instead of a space,' \
                 ' use this symbols #_#' \
                 '\nExample: My Folder = My#_#Folder' \
                 '\nYou can exit the program' \
                 ' by writing in the hostname field "close", "exit" or "quit"\n\n'
        f_help = ['{}: {}'.format(k, v['help']) for k, v in self.get_cmd().items()]
        return notice + '\n'.join(f_help)

    def get_func(self):
        return {k: v['func'] for k, v in self.get_cmd().items()}


def print_help(cmd_class):
    print(cmd_class.get_help())


def command_handler(command_class, cmd, ftp):
    func = command_class.get_func()
    if isinstance(cmd, str) and cmd.lower().startswith('send '):
        print_result(ftp.send_command(cmd[5:]))
        return
    elif not isinstance(cmd[0], str) or not isinstance(cmd, list):
        print_result('Wrong input.')
        return
    elif cmd[0].lower().startswith('help'):
        print_help(command_class)
    elif cmd[0].upper() in func.keys():
        cmd[0] = cmd[0].upper()
        if len(cmd) == 1:
            print_result(func[cmd[0]]())
            if cmd[0] == 'QUIT':
                return 'QUIT'
        elif len(cmd) == 2:
            print_result(func[cmd[0]](cmd[1]))
        elif len(cmd) == 3:
            print_result(func[cmd[0]](cmd[1], cmd[2]))
    else:
        print_result('Unknown command. Use "Help".')


def receive_command(ftp):
    while True:
        cmd = get_cmd('Next command: ')
        if command_handler(Command(ftp), cmd, ftp) == 'QUIT':
            return 'QUIT'


def create_receiver(host, settings=None):
    if settings is not None:
        ftp = FTPclient.FTP(host=settings[0])
        print_result(ftp.login(settings[1], settings[2]))
    else:
        ftp = FTPclient.FTP()
        try:
            print_result(ftp.connect(host))
        except:
            print_result('Cant connect to ' + host)
            return 'nothing'
        username = input('Username: ')
        password = input('Password: ')
        result = ftp.login(username, password)
        print_result(result)
        if result[0] in ['4', '5']:
            return 'nothing'
    if receive_command(ftp) == 'QUIT':
        return 'QUIT'


def start_console_ftp(settings=None):
    print_result('Hi, this is a small FTP client')
    while True:
        try:
            if settings is None:
                host = input(MSG_WITHOUT_SETTINGS)
            else:
                host = input(MSG_WITH_SETTINGS)
            if host.lower() in {'stop', 'close', 'quit', 'exit'}:
                print_result('Goodbye')
                break
            elif host.lower() == 'help':
                print_help(Command())
            else:
                res = create_receiver(host, settings).lower()
                if res == 'quit':
                    ans = input('Stop the program (y/n)? ')
                    if ans in {'y', 'yes', 'yep', 'yea', 'fortest'}:
                        print_result('Goodbye')
                        break
        except Exception as e:
            print_result('Что-то пошло не так. \n' + str(e))


def get_settings(fname):
    try:
        with open(fname) as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        return [x.split('=')[1] for x in content]
    except (IOError, IndexError):
        return None


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Light ftp client',
        epilog='Author: {} <{}>'.format(__author__, __email__))
    arg_group = parser.add_mutually_exclusive_group()
    arg_group.add_argument(
        '-s', '--stor', nargs=1, type=str,
        metavar='FILE',
        help='upload the file to the server with using data from settings')
    arg_group.add_argument(
        '-r', '--retr', nargs=1, type=str,
        metavar='FILE',
        help='download the file from server with using data from settings')
    return parser.parse_args(args)


def main():
    settings = get_settings('settings.txt')
    args = parse_args(sys.argv[1:])
    if args.stor is not None or args.retr is not None:
        stor_path = None
        retr_name = None
        if args.stor[0] is not None:
            stor_path = args.stor[0]
        elif args.retr[0] is not None:
            retr_name = args.retr[0]
        if settings is not None:
            ftp = FTPclient.FTP(host=settings[0])
            ftp.login(settings[1], settings[2])
            if stor_path:
                ftp.stor(stor_path)
            elif retr_name:
                ftp.retr(retr_name)
        else:
            print('For correct operation configure the settings')
    else:
        start_console_ftp(settings)


if __name__ == '__main__':
    main()
