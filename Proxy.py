#!/usr/bin/env python3.10
from socket import*
import sys
import time
import re
from threading import Thread

throughput ={}
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
            client_thread.daemon = True
            client_thread.start()

        except Exception as e:
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

            chunk_name, domain = GetNames(primemessage)
            server_ip = GetIp(dnsserver_port, domain)

            if not chunk_name or not domain:
                print("Invalid Request")
                break
            if not server_ip:
                print("server IP not found")
                break

            pair_key = (client_ip, server_ip)
            t_current = throughput.get(pair_key, 100)  ##initialization

            manifest_data = FetchManifest(server_ip, "BigBuckBunny_6s.mpd", fake_ip)
            if not manifest_data:
                print("Fetching Manifest Data Failed")
                break
            
            bitrates_option = ParseManifest(manifest_data)
                            
            if "BigBuckBunny_6s_nolist.mpd" in chunk_name:
                no_list = FetchManifest(server_ip, chunk_name, fake_ip)
                if no_list:
                    connectionSocket.sendall(no_list)
                continue

            #select the certificated bitrate
            selected_bitrate = SelectBitRate(bitrates_option, t_current)

            #modefy the message
            modified_message = Modify(primemessage, selected_bitrate)
            modified_chunk, _ = GetNames(modified_message)

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

                Log(log_file, duration, t_new, t_current, selected_bitrate, server_ip, modified_chunk)

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


def GetNames(primemessage):
    try:
        decoded = primemessage.decode()
        lines = decoded.split('\n')
        chunk_name = lines[0].split(' ')[1]
        domain = lines[1].strip().split(' ')[1]
        return chunk_name, domain
    except IndexError:
        return None, None

def Log(log_file, duration, tput, avg_tput, chunk_bitrate, server_ip, chunk_name):
    log_time = time.time()
    tput = tput/1000
    avg_tput = avg_tput/1000
    chunk_bitrate = chunk_bitrate/1000
    result = f"{log_time} {duration:.3f} {tput:.2f} {avg_tput:.2f} {chunk_bitrate:.2f} {server_ip} {chunk_name}\n"
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

def GetIp(server_port, message):
    try:
        dnssocket = socket(AF_INET, SOCK_DGRAM)
        dnssocket.sendto(message.encode('utf-8'),('127.0.0.1', server_port))
        server_ip, _ = dnssocket.recvfrom(1024)
        dnssocket.close()
        result = Extract(server_ip)
        if not result:
            return None
        else:
            return result
    except (OSError, ConnectionRefusedError):
        return None
    finally:
        dnssocket.close()

def FetchManifest(server_ip, chunk_name, fake_ip):
    #fetch manifest file from the server
    try:
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind((fake_ip,0))
        serverSocket.connect((server_ip, 80))
        request = f"GET {chunk_name} HTTP/1.1\r\nHost:{server_ip}\r\n\r\n"
        serverSocket.sendall((request.encode))

        manifest_data = serverSocket.recv(4096)
        if not manifest_data:
            return None
        return manifest_data
    except Exception as e:
        return None
    finally:
        if serverSocket:
            serverSocket.close()
    
def ParseManifest(manifest_data):
    # parese the optional bitrates using regex
    bitrates = []
    try:
        #find all values that indicated by <Representation bandwidth="value">
        values = re.findall(r'<Representation.*?bandwidth="(\d+)"', manifest_data.decode())
        bitrates = sorted(int(bandwidth) for bandwidth in values)
    except Exception as e:
        print(f"Error parsing manifest: {e}")
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

def Extract(response):
    try:
        header = 12
        question_end = header
        while response[question_end] != 0:
            question_end += 1
        question_end += 1
        answerin = question_end + 4
        answerbyte = response[answerin+10: answerin+14]
        ip = '.'.join(map(str,answerbyte))
        return ip
    except IndexError as e:
        print("DNS response Error")
        return None

if __name__ == "__main__":
    topo_dir = sys.argv[1]
    log_file = sys.argv[2]
    alpha = float(sys.argv[3])
    listen_port = int(sys.argv[4])
    fake_ip = sys.argv[5]
    dns_server_port = int(sys.argv[6])
    Proxy(log_file, alpha, listen_port, fake_ip, dns_server_port)
