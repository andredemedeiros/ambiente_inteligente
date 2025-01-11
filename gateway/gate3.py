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
TCP_PORT = 6000  # Porta para comunicação com o cliente
BUFFER_SIZE = int(env.BUFFER_SIZE)

devices = []  # Lista de dispositivos disponíveis via multicast UDP
client_socket = None  # Conexão com o cliente

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
    print(f'Enviando mensagens via multicast ({MCAST_GRP}:{MCAST_PORT}).')
    while True:
        try:
            message = json.dumps(MCAST_MSG)
            sock.sendto(message.encode('utf-8'), (MCAST_GRP, int(MCAST_PORT)))
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
                achou = 0
                for dev in devices:
                    if dev['BLOCO'] == device_bloc:
                        dev['IP'] = device_ip
                        dev['PORTA ENVIO TCP'] = device_port
                        achou = 1
                        break
                if achou == 0:
                    devices.append(data_json)
                    print(f"Novo dispositivo encontrado via multicast: {data_json}")
        except socket.timeout:
            continue

def listen_for_sensor_data():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', GTW_UDP_PORT))  # Bind para escutar a porta UDP do sensor

    while True:
        try:
            # Recebe os dados do sensor
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            sensor_data = json.loads(data.decode('utf-8'))
            print(f"Dado recebido do sensor: {sensor_data}")

            # Encaminha os dados do sensor para o cliente conectado
            if client_socket:
                try:
                    client_socket.send(json.dumps(sensor_data).encode('utf-8'))
                except Exception as e:
                    print(f"Erro ao enviar dados do sensor para o cliente: {e}")
        except Exception as e:
            print(f"Erro ao receber dados UDP: {e}")

def handle_client_connection():
    global client_socket
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind((GTW_IP, TCP_PORT))
    tcp_socket.listen(1)  # Aceitar apenas um cliente por vez
    print(f"Gateway aguardando conexão de cliente na porta {TCP_PORT}.")

    while True:
        client_socket, client_address = tcp_socket.accept()
        print(f"Cliente conectado: {client_address}")

        try:
            while True:
                # Receber comandos do cliente
                command = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not command:
                    break
                print(f"Comando recebido do cliente: {command}")

                # Interpretar e enviar o comando para os dispositivos
                command_data = json.loads(command)
                device_bloc = command_data.get("BLOCO")
                state = command_data.get("STATE")

                # Procurar o dispositivo e enviar o comando
                for dev in devices:
                    if dev['BLOCO'] == device_bloc:
                        change_device_state(
                            device_bloc, dev['IP'], dev['PORTA ENVIO TCP'], state
                        )
                        break
        except Exception as e:
            print(f"Erro na conexão com o cliente: {e}")
        finally:
            client_socket.close()
            client_socket = None
            print("Cliente desconectado.")

def change_device_state(device_bloc, device_ip, device_port, state):
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(10)
        tcp_socket.connect((device_ip, int(device_port)))
        tcp_socket.send(state.encode())
        print(f"Estado {state} enviado para dispositivo do bloco {device_bloc}.")
    except (socket.timeout, socket.error) as e:
        print(f"Erro na conexão com {device_ip}:{device_port} - {e}")
        devices[:] = [dev for dev in devices if not (dev['IP'] == device_ip and dev['PORTA ENVIO TCP'] == device_port)]
        print(f"Dispositivo do bloco {device_bloc} removido.")
    finally:
        tcp_socket.close()

def main():
    threading.Thread(target=send_multicast_gtw, daemon=True).start()
    threading.Thread(target=discover_devices, daemon=True).start()
    threading.Thread(target=listen_for_sensor_data, daemon=True).start()
    threading.Thread(target=handle_client_connection, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
