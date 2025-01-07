import socket
import struct
import threading
import time

# Configurações
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 5007
TCP_PORT = 5008
BUFFER_SIZE = 1024

# Função para descobrir dispositivos via multicast UDP
def discover_devices():
    # Cria o socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', MULTICAST_PORT))

    # Adiciona o socket à lista de multicast
    mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            print(f"Dispositivo encontrado: {addr}")
        except socket.timeout:
            continue

# Função para enviar dados via TCP para os dispositivos
def send_data_to_devices():
    # Cria o socket TCP para o gateway
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('', TCP_PORT))
    tcp_socket.listen(5)

    print(f"Gateway ouvindo na porta TCP {TCP_PORT}...")

    while True:
        client_socket, client_address = tcp_socket.accept()
        print(f"Conectado ao dispositivo {client_address}")
        
        # Envia dados periodicamente
        while True:
            message = "Mensagem do Gateway"
            client_socket.send(message.encode())
            print(f"Mensagem enviada para {client_address}: {message}")
            time.sleep(5)

# Função principal que gerencia as threads
def main():
    # Thread para descobrir dispositivos via UDP
    udp_thread = threading.Thread(target=discover_devices)
    udp_thread.daemon = True
    udp_thread.start()

    # Thread para enviar dados via TCP
    tcp_thread = threading.Thread(target=send_data_to_devices)
    tcp_thread.daemon = True
    tcp_thread.start()

    # Mantém o programa rodando
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
