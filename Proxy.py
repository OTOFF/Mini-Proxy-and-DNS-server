#!/usr/bin/env python3.10
from socket import*
import sys

def Proxy(port, fake_ip, server_ip):
## listen from the client
    ListenSocket = socket(AF_INET, SOCK_STREAM)
    ListenSocket.bind(('', port))
    ListenSocket.listen(1)
    print("Proxy is ready to receive on ", port)

    while True:
        try:
            connectionSocket, addr = ListenSocket.accept()
            primemessage = connectionSocket.recv(2048)
            decoded = primemessage.decode()
            check = Verify(decoded)
        
            if check:
                ## send the message to server if message is valid(ie.has EMO)
                serverSocket = socket(AF_INET, SOCK_STREAM)
                serverSocket.bind((fake_ip, 0))

                ##close the proxy if server disconnected
                try:
                    serverSocket.connect((server_ip, 8080))
                    serverSocket.send(primemessage)
                    primeresponse = serverSocket.recv(2048)
                    connectionSocket.send(primeresponse)
                except (OSError, ConnectionRefusedError) as e:
                    ListenSocket.close()
                    connectionSocket.close()
                    serverSocket.close()

            ## not sending the message when it misses '\n'         
            else:
                print("message is not complete.")

        except (OSError, ConnectionRefusedError) as e:
            ListenSocket.close()
            connectionSocket.close()
        
        if serverSocket:
            serverSocket.close()
        if connectionSocket:
            connectionSocket.close()

# to capture only the message before EOM
def Verify(message):
    result = True
    if '\n' not in message:
        result = False
    return result

if __name__ == "__main__":
    port = int(sys.argv[1])
    fake_ip = sys.argv[2]
    server_ip = sys.argv[3]
    Proxy(port, fake_ip, server_ip)
