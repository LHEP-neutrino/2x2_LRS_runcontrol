import socket


SENDER_HOST = 'localhost'
SENDER_PORT_ADC64 = 6000
SENDER_PORT_RC = 6001


class Sender:
    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((SENDER_HOST, self.port))

    def msg_send(self, msg):
        self.sock.send(msg.encode())
