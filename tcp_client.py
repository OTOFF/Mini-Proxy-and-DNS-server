from socket import *

clientSocket = socket(AF_INET, SOCK_STREAM)

serverName = 'localhost'
serverPort = 1235

message = 'hello world \n'

# Connect to the server's listening socket
clientSocket.connect((serverName, serverPort))

print("Sending Message to Server: ", message)

# Encode the message into binary
encodedMessage = message.encode()

# Send the encoded message to the server
clientSocket.send(encodedMessage)

# Receive the modified message back from the server
encodedServerMessage = clientSocket.recv(2048)

# Decode the modified message back into a string
decodedServerMessage = encodedServerMessage.decode()

print("Received Message from Server: ", decodedServerMessage)


clientSocket.close()
