import socket
import struct
import threading
import time
import json

# Configurações
MCAST_GRP = '228.0.0.8'
MCAST_PORT = 6789

UDP_PORT = 12345  # Porta para receber dados UDP de sensores

BUFFER_SIZE = 1024

devices = []  # Lista de dispositivos conectados

# Função para descobrir dispositivos via multicast UDP
def discover_devices():
    # Cria o socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', MCAST_PORT))

    # Adiciona o socket à lista de multicast
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        try:
            # Aguarda a resposta de um dispositivo
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)

            device_ip = addr[0]  # Extraímos apenas o IP do dispositivo
            device_port = "40" + data.decode('utf-8')

            device_tuple = (device_ip, device_port)
            
            if device_tuple not in devices:
                print(f"Dispositivo encontrado: {device_ip} na porta {device_port}")
                devices.append(device_tuple)
            else:
                print(f"Dispositivo {device_ip} já foi registrado (porta {device_port}).")
            
        except socket.timeout:
            continue

# Função para gerenciar a conexão TCP persistente
def change_device_state(device_ip, device_port, state):
    try:
        # Cria o socket TCP
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(10)  # Timeout para evitar bloqueios infinitos
        tcp_socket.connect((device_ip, int(device_port)))
        print(f"Conectado ao dispositivo {device_ip} na porta {device_port}")

        message = state
        tcp_socket.send(message.encode())
        print(f"Mensagem enviada para {device_ip}: {message}")
        time.sleep(5)

    except (socket.timeout, socket.error) as e:
        print(f"Falha na conexão TCP com {device_ip}:{device_port} - Erro: {e}")
    finally:
        tcp_socket.close()
        print(f"Conexão com {device_ip}:{device_port} fechada.")

# Função para escutar os dados UDP de sensor
def listen_for_sensor_data():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', UDP_PORT))  # Bind para escutar a porta UDP de sensor

    while True:
        try:
            # Recebe os dados do sensor
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)

            # Decodifica os dados recebidos, espera um JSON com dados do sensor
            sensor_data = json.loads(data.decode('utf-8'))
            print(f"Dados de sensor recebidos de {addr}: {sensor_data}")

        except Exception as e:
            print(f"Erro ao receber dados UDP: {e}")

# Função principal que gerencia as threads
def main():

    # Descobrir dispositivos via multicast UDP
    udp_thread = threading.Thread(target=discover_devices)
    udp_thread.daemon = True
    udp_thread.start()

    # Escutar dados de sensores via UDP
    sensor_thread = threading.Thread(target=listen_for_sensor_data)
    sensor_thread.daemon = True
    sensor_thread.start()

    # Altera estados dos dispositivos através de conexão TCP
    while True:

        for device_ip, device_port in devices:
            change_device_state(device_ip, device_port, "0")

        time.sleep(15)

if __name__ == "__main__":
    main()
