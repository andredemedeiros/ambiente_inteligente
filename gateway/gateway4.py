import socket
import struct
import threading
import time
import json
import box
from dotenv import dotenv_values

# Configurações
env = box.Box(dotenv_values(".env"))

MCAST_GRP = env.MCAST_GRP
MCAST_PORT = int(env.MCAST_PORT)
GTW_IP = env.GTW_IP
GTW_UDP_PORT = int(env.GTW_UDP_PORT)  # Porta para receber dados UDP de sensores
BUFFER_SIZE = int(env.BUFFER_SIZE)
TCP_PORT = 6000  # Porta TCP para comunicação com o cliente

devices = []  # Lista de dispositivos disponíveis via multicast UDP
sensor_data_queue = []  # Fila para armazenar dados de sensores

def send_multicast_gtw():
    MCAST_MSG = {
        'TIPO': "GTW",
        'GTW ID': 1,
        'IP': GTW_IP,
        'PORTA ENVIO UDP': GTW_UDP_PORT
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    while True:
        try:
            message = json.dumps(MCAST_MSG)
            sock.sendto(message.encode('utf-8'), (MCAST_GRP, MCAST_PORT))
            time.sleep(5)
        except Exception as e:
            print(f"Erro ao enviar a mensagem: {e}")
            break
    sock.close()

def discover_devices():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            data_json = json.loads(data.decode('utf-8'))
            if data_json["TIPO"] == "DEVICE":
                device_bloc = data_json.get("BLOCO")
                device_ip = data_json.get("IP")
                device_port = data_json.get("PORTA ENVIO TCP")

                for dev in devices:
                    if dev['BLOCO'] == device_bloc:
                        dev['IP'] = device_ip
                        dev['PORTA ENVIO TCP'] = device_port
                        break
                else:
                    devices.append(data_json)
                    print(f"Novo dispositivo encontrado via multicast: {data_json}")
        except socket.timeout:
            continue

def listen_for_sensor_data():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', GTW_UDP_PORT))

    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            sensor_data = json.loads(data.decode('utf-8'))
            print(f"Dado recebido: {sensor_data}")
            sensor_data_queue.append(sensor_data)
        except Exception as e:
            print(f"Erro ao receber dados UDP: {e}")

def tcp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((GTW_IP, TCP_PORT))
    server_socket.listen(1)
    print(f"Servidor TCP escutando na porta {TCP_PORT}...")

    while True:
        client_socket, client_addr = server_socket.accept()
        print(f"Cliente conectado: {client_addr}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

def handle_client(client_socket):
    try:
        while True:
            # Envia dados do sensor para o cliente
            if sensor_data_queue:
                sensor_data = sensor_data_queue.pop(0)
                client_socket.sendall(json.dumps(sensor_data).encode('utf-8'))

            # Recebe comandos do cliente
            command = client_socket.recv(1024).decode('utf-8')
            if command.startswith("SET_STATE"):
                _, bloc, state = command.split()
                for dev in devices:
                    if dev["BLOCO"] == bloc:
                        change_device_state(bloc, dev["IP"], dev["PORTA ENVIO TCP"], state)
 
            elif command.startswith("RECIEVE_DATA"):
                _, bloc, state = command.split()
                for dev in devices:
                    if dev["BLOCO"] == bloc:
                        change_device_state(bloc, dev["IP"], dev["PORTA ENVIO TCP"], state)
    except Exception as e:
        print(f"Erro no cliente: {e}")
    finally:
        client_socket.close()

def change_device_state(device_bloc, device_ip, device_port, state):
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(10)
        tcp_socket.connect((device_ip, int(device_port)))
        tcp_socket.send(state.encode())
        print(f"Estado {state} enviado para bloco {device_bloc}")
    except (socket.timeout, socket.error) as e:
        print(f"Erro na conexão TCP com {device_ip}:{device_port} - {e}")
        devices[:] = [dev for dev in devices if not (dev['IP'] == device_ip and dev['PORTA ENVIO TCP'] == device_port)]
    finally:
        tcp_socket.close()

def main():
    threading.Thread(target=send_multicast_gtw, daemon=True).start()
    threading.Thread(target=discover_devices, daemon=True).start()
    threading.Thread(target=listen_for_sensor_data, daemon=True).start()
    threading.Thread(target=tcp_server, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
