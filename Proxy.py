#!/usr/bin/env python3.10
from socket import*
import sys
import time
import re
from threading import Thread

throughput ={}
bitrates_option = {}
def Proxy(log_file, alpha, port, fake_ip, dnsserver_port):
## listen from the client

    ListenSocket = socket(AF_INET, SOCK_STREAM)
    ListenSocket.bind(('', port))
    ListenSocket.listen(100)

    while True:
        try:
            connectionSocket, addr = ListenSocket.accept()
            client_ip = addr[0]
            client_thread = Thread(target=client, args=(connectionSocket, log_file, alpha, client_ip, fake_ip, dnsserver_port))
            client_thread.start()

        except (OSError, ConnectionRefusedError) as e:
            break

    if ListenSocket:
        ListenSocket.close()




def client(connectionSocket, log_file, alpha, client_ip, fake_ip, dnsserver_port):
    global throughput

    try:
        while True:
            primemessage = connectionSocket.recv(2048)

            if not primemessage:
                print("Client disconnected")
                break

            chunk_name = GetName(primemessage)
            server_ip = GetIp(dnsserver_port, chunk_name)

            #when request is manifest file; load in the optional bitrates in the proxy only
            if "BigBuckBunny_6s.mpd" in chunk_name:
                manifest_data = FetchManifest(server_ip, chunk_name, fake_ip)
                bitrates_option[chunk_name] = ParseManifest(manifest_data)

                #send the modified no list mpd to the client
                no_list = FetchManifest(server_ip, "BigBuckBunny_6s_nolist.mpd", fake_ip)
                connectionSocket.sendall(no_list)
                continue

            if not server_ip:
                print("server IP not found")
                break

            pair_key = (client_ip, server_ip)
            t_current = throughput.get(pair_key, 100)  ##initialization

            #select the certificated bitrate
            selected_bitrate = SelectBitRate(bitrates_option[chunk_name], t_current)

            #modefy the message
            modified_message = Modify(primemessage, selected_bitrate)

            try:
                serverSocket = socket(AF_INET, SOCK_STREAM)
                serverSocket.bind((fake_ip, 0))
                serverSocket.connect((server_ip, 80))
                serverSocket.sendall(modified_message)
                        
                starttime = time.time()
                primeresponse = serverSocket.recv(2048)
                endtime = time.time()
                duration = endtime - starttime

                if not primeresponse:
                    break

                chunk_size = GetLength(primeresponse)
                
                # Calculate throughput and record into the throughput dictionary
                t_new = chunk_size / duration if duration > 0 else 0
                t_current = alpha*t_new + (1-alpha) * t_current
                throughput[pair_key] = t_current

                Log(log_file, duration, t_new, t_current, selected_bitrate, server_ip, chunk_name)

                connectionSocket.sendall(primeresponse)

            except (OSError, ConnectionRefusedError) as e:
                serverSocket.close()
                break

    except (OSError, ConnectionRefusedError) as e:
        print("connection failed")
    finally:
        if connectionSocket:
            connectionSocket.close()
        if serverSocket:
            serverSocket.close()



# to capture only the message before EOM
def GetName(primemessage):
    try:
        decoded = primemessage.decode()
        line = decoded.split('\n')[0]
        chunk_name = line.split(' ')[1]
        return chunk_name
    except IndexError:
        return "Invalid Message"

def Log(log_file, duration, tput, avg_tput, chunk_bitrate, server_ip, chunk_name):
    log_time = time.time()
    tput = tput/1000
    avg_tput = avg_tput/1000
    chunk_bitrate = chunk_bitrate/1000
    result = f"{log_time} {duration} {tput} {avg_tput} {chunk_bitrate} {server_ip} {chunk_name} \n"
    with open (log_file, 'a') as f:
        f.write(result)
        f.flush()

def GetLength(primeresponse):
    try:
        header, body = primeresponse.split(b'\r\n\r\n',1)
        contents = header.decode().split('\r\n')
        for line in contents:
            if line.startswith("Content-Length:"):
                return int(line.split(":")[1].strip())
    except (ValueError, IndexError):
        return len(primeresponse)

def GetIp(server_port, chunkname):
    try:
        dnssocket = socket(AF_INET, SOCK_DGRAM)
        dnssocket.sendto(chunkname.encode(),('127.0.0.1', server_port))
        server_ip, _ = dnssocket.recvfrom(1024)
        dnssocket.close()
        return server_ip.decode()
    except (OSError, ConnectionRefusedError):
        return None

def FetchManifest(server_ip, chunk_name, fake_ip):
    #fetch manifest file from the server
    try:
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind((fake_ip,0))
        serverSocket.connect((server_ip, 80))
        request = f"GET {chunk_name} HTTP/1.1\r\nHost:{server_ip}\r\n\r\n"
        serverSocket.sendall((request.encode))

        manifest_data = serverSocket.recv(4096)
        serverSocket.close()
        return manifest_data
    except Exception as e:
        return None
    
def ParseManifest(manifest_data):
    # parese the optional bitrates using regex
    bitrates = []
    #find all values that indicated by <Representation bandwidth="value">
    values = re.findall(r'<Representation.*?bandwidth="(\d+)"', manifest_data)
    bitrates = sorted(int(bandwidth) for bandwidth in values)
    return bitrates

def SelectBitRate(bitrate_options, t_current):
    #check from the highest bitrate
    for rate in reversed(bitrate_options):
        if t_current >= 1.5*rate:
            return rate
    return bitrate_options[0]

def Modify(message, bitrate):
    #modify the URI in the request to the selected bitrate label
    modified = re.sub(r"bunny_\d+bps", f"bunny_{bitrate}bps", message.decode())
    return modified.encode()

if __name__ == "__main__":
    topo_dir = sys.argv[1]
    log_file = sys.argv[2]
    alpha = float(sys.argv[3])
    listen_port = int(sys.argv[4])
    fake_ip = sys.argv[5]
    dns_server_port = int(sys.argv[6])
    Proxy(log_file, alpha, listen_port, fake_ip, dns_server_port)
