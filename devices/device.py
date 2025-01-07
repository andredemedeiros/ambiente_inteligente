import socket
import struct
import threading
import time

# Configurações
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 5007
UDP_PORT = 5009
BUFFER_SIZE = 1024
GATEWAY_DISCOVERY_INTERVAL = 5  # Intervalo para reenviar descoberta

# Função para enviar dados para o gateway via UDP
def send_data_to_gateway():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Substitua '127.0.0.1' pelo IP do seu gateway, por exemplo:
    gateway_ip = '127.0.0.1'  # IP do Gateway
    gateway_port = 5008  # Porta TCP do gateway

    while True:
        data = "Dados do dispositivo"
        udp_socket.sendto(data.encode(), (gateway_ip, gateway_port))
        print(f"Dispositivo enviando dados: {data}")
        time.sleep(5)

# Função para descobrir o gateway via multicast UDP
def discover_gateway():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', MULTICAST_PORT))

    # Adiciona o socket à lista de multicast
    mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            print(f"Descobriu o gateway: {addr}")
        except socket.timeout:
            continue

# Função principal que gerencia as threads
def main():
    # Thread para descobrir o gateway via UDP
    discovery_thread = threading.Thread(target=discover_gateway)
    discovery_thread.daemon = True
    discovery_thread.start()

    # Thread para enviar dados via UDP
    send_thread = threading.Thread(target=send_data_to_gateway)
    send_thread.daemon = True
    send_thread.start()

    # Mantém o dispositivo rodando
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
