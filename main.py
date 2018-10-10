import select
import signal
import socket
import threading
import pickle
import struct
import argparse
import sys

SERVER_HOST = 'localhost'
CHAT_SERVER_NAME = 'server'

def send(channel, *args):
    buffer = pickle.dumps(args)
    value = socket.htonl(len(buffer))
    size = struct.pack("L", value)
    channel.send(size)
    channel.send(buffer)

def receive(channel):
    size = struct.calcsize("L")
    size = channel.recv(size)
    try:
        size = socket.ntohl(struct.unpack("L", size)[0])
    except struct.error as e:
        return ''
    buf = ""
    while len(buf) < size:
        buf = channel.recv(size - len(buf))
    return pickle.loads(buf)[0]

class ChatServer(object):
    def __init__(self, port, backlog=5):
        self.clients = 0
        self.clientmap = {}
        self.outputs = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        self.server.listen(backlog)
        signal.signal(signal.SIGINT, self.sighandler)

    def sighandler(self, signum, frame):
        print('Shutting down server')
        for output in self.outputs:
            output.close()
        self.server.close()

    def get_client_name(self, client):
        info = self.clientmap[client]
        host, name = info[0][0], info[1]
        return '@'.join((name, host))

    def run(self):
        inputs = [self.server]
        self.outputs = []
        running = True
        print(inputs)
        print(self.outputs)
        while running:
            try:
                print(1)
                readable, writeable, exceptional= select.select(inputs, self.outputs, [])
                print(2)
                for sock in readable:
                    if sock == self.server:
                        client, address = self.server.accept()
                        print('Got Connection from %s' % (client.fileno()))
                        cname = receive(client).split('NAME: ')[1]
                        self.clients += 1
                        send(client, 'CLIENT: ' + str(address[0]))
                        inputs.append(client)
                        self.clientmap[client] == (address, cname)
                        msg = '%s' % (self.get_client_name(client))
                        for output in self.outputs:
                            send(output, msg)
                        self.outputs.append(client)
                    elif sock == sys.stdin:
                        junk = sys.stdin.readline()
                        running = False
                    else:
                        try:
                            data = receive(sock)
                            if data:
                                msg = data
                                for output in self.outputs:
                                    if output != sock:
                                        send(output, msg)
                            else:
                                print('ok')
                                sock.fileno()
                                self.clients -= 1
                                sock.close()
                                inputs.remove(sock)
                                self.outputs.remove(sock)
                                for output in self.outputs:
                                    send(output, 'ok')
                        except socket.error as e:
                            inputs.remove(sock)
                            self.outputs.remove(sock)

            except Exception as e:
                print(e)
                break


class ChatClient(object):
    def __init__(self, name, port, host=SERVER_HOST):
        self.name = name
        self.connected = False
        self.host = host
        self.port = port
        self.prompt = 'a'
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, self.port))
            self.connected = True
            send(self.sock, 'NAME: ' + self.name)
            data = receive(self.sock)
            addr = data.split('CLIENT: ')[1]
            self.prompt = addr
        except socket.error as e:
            print(e)
            sys.exit(1)
    def run(self):
        while self.connected:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()
                readable, w, e = select.select([self.sock], [], [])
                for sock in readable:
                    if sock == 0:
                        data == sys.stdin.readline().strip()
                        if data : send(self.sock, data)
                    elif sock == self.sock:
                        data = readable(self.sock)
                        if not data:
                            self.connected = False
                            break
                        else:
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()
            except KeyboardInterrupt:
                self.sock.close()
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='socket server')
    parser.add_argument('--name', action='store', dest='name', required=True)
    parser.add_argument('--port', action='store', dest='port', type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port
    name = given_args.name
    if name == CHAT_SERVER_NAME:
        server = ChatServer(port)
        server.run()
    else:
        client = ChatClient(name=name, port=port)
        client.run()
