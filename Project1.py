from socket import*
import sys

def Proxy(port, fake_ip, server_ip):
    ListenSocket = socket(AF_INET, SOCK_STREAM)
    ListenSocket.bind(('', port))
    ListenSocket.listen(1)
    print("Proxy is ready to receive on ", port)

    while True:

        connectionSocket, addr = ListenSocket.accept()
        print(f"Connection established with {addr}")

        primemessage = connectionSocket.recv(2048)
        decoded = primemessage.decode()
        message = FindMes(decoded)
        print("Received Message from Client: ", message)

        encodedm = message.encode()

        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind((fake_ip, 0))
        serverSocket.connect(('', 8080))
        serverSocket.send(encodedm)
        print("Sending", message, "to Server: 8080")

        primeresponse = serverSocket.recv(2048)
        print("Received Message from Server: ", primeresponse.decode())
        connectionSocket.send(primeresponse)

        if serverSocket:
            serverSocket.close()
        if connectionSocket:
            connectionSocket.close()

def FindMes(message):
    result = ''
    for i in message:
        result += i
        if i == '\n':
            break
    return result

if __name__ == "__main__":
    port = int(sys.argv[1])
    fake_ip = sys.argv[2]
    server_ip = sys.argv[3]
    Proxy(port, fake_ip, server_ip)
