from socket import *
import time

serverSocket = socket(AF_INET, SOCK_STREAM)

serverSocket.bind(('' , 8080))

serverSocket.listen(1)

print("Server is ready to receive on port 1234...")

while 1==1:

  connectionSocket, addr = serverSocket.accept()
  
  print(f"Connection established with {addr}")

  # Recieving message from client
  encodedClientMessage = connectionSocket.recv(2048)

  # Decode the recieved binary message into a string
  decodedClientMessage = encodedClientMessage.decode()

  print("Received Message from Client: ", decodedClientMessage)

  time.sleep(3)

  # Modifying the message
  modifiedClientMessage = decodedClientMessage.upper()

  print("Sending Message to Client: ", modifiedClientMessage)

  # Encode the modified message back into binary
  encodedClientModifiedMessage = modifiedClientMessage.encode()

  # Sending the encoded modified message back to the client
  connectionSocket.send(encodedClientModifiedMessage)

  connectionSocket.close()
  
serverSocket.close()
