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

devices = []  # Lista de dispositivos disponíveis via multicast UDP

def send_multicast_gtw():
    MCAST_GRP = env.MCAST_GRP
    MCAST_PORT = env.MCAST_PORT

    MCAST_MSG = {
        'TIPO': "GTW",
        'GTW ID': 1,
        'IP': GTW_IP, 
        'PORTA ENVIO UDP': GTW_UDP_PORT
    }

    # Criação do socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Definindo o TTL para o pacote multicast (valor padrão 1 significa "só na rede local")
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Loop para enviar a mensagem periodicamente
    while True:
        try:
            # Serializando a mensagem para JSON antes de enviar
            message = json.dumps(MCAST_MSG)

            # Enviar a mensagem multicast
            sock.sendto(message.encode('utf-8'), (MCAST_GRP, int(MCAST_PORT)))
            print(f'Mensagem enviada para {MCAST_GRP}:{MCAST_PORT}.')

            # Aguardar o próximo envio (intervalo de 5 segundos, por exemplo)
            time.sleep(5)

        except Exception as e:
            print(f"Erro ao enviar a mensagem: {e}")
            break

    sock.close() 

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

            data_json = json.loads(data.decode('utf-8'))
            
            # Verifica se é do tipo "Device"
            if data_json["TIPO"] == "DEVICE":
                
                
                # Verificar se o dispositivo referente ao bloco já foi adicionado à lista de dispositivos
                device_bloc = data_json.get("BLOCO")
                device_ip = data_json.get("IP")  # Extraímos o IP do dispositivo
                device_port = data_json.get("PORTA ENVIO TCP")

                achou = 0
                # Atualizar o dispositivo existente com o novo IP e porta
                for dev in devices:
                    if dev['BLOCO'] == device_bloc:
                        dev['IP'] = device_ip
                        dev['PORTA ENVIO TCP'] = device_port
                        print(f"Dispositivo {device_bloc} atualizado com o novo IP: {device_ip} e porta: {device_port}")
                        achou = 1
                        break

                if achou == 0:
                    devices.append(data_json)
                    print(f"Novo dispositivo encontrado: {data_json}")

        except socket.timeout:
            continue

# Função para escutar dados UDP's de sensores
def listen_for_sensor_data():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', GTW_UDP_PORT))  # Bind para escutar a porta UDP do sensor

    while True:
        try:
            # Recebe os dados do sensor
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)

            # Decodifica os dados recebidos, espera um JSON com dados do sensor
            sensor_data = json.loads(data.decode('utf-8'))
            print(f"Dados de sensor recebidos de {addr}: {sensor_data}")

        except Exception as e:
            print(f"Erro ao receber dados UDP: {e}")

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
        # Remove o dispositivo da lista de dispositivos caso haja erro de conexão
        devices[:] = [dev for dev in devices if not (dev['IP'] == device_ip and dev['PORTA ENVIO TCP'] == device_port)]
        print(f"Dispositivo {device_ip}:{device_port} removido da lista de dispositivos.")
        tcp_socket.close()
        
    finally:
        tcp_socket.close()
        print(f"Conexão com {device_ip}:{device_port} fechada.")

# Função principal que gerencia as threads
def main():

    # Thread de apresentação como gtw ao grupo multicast 
    send_multicast_gtw_thread = threading.Thread(target=send_multicast_gtw)
    send_multicast_gtw_thread.daemon = True
    send_multicast_gtw_thread.start()

    # Thread que armazena os dispositivos via multicast UDP
    recv_multicast_gtw_thread = threading.Thread(target=discover_devices)
    recv_multicast_gtw_thread.daemon = True
    recv_multicast_gtw_thread.start()

    # Escutar dados de sensores via UDP
    recv_sensor_data_thread = threading.Thread(target=listen_for_sensor_data)
    recv_sensor_data_thread.daemon = True
    recv_sensor_data_thread.start()

    # Muda estado de dispositivos através de conexão TCP
    while True:

        for dev in devices:
           device_ip = dev.get("IP")
           device_port = dev.get("PORTA ENVIO TCP")

           change_device_state(device_ip, device_port, "0")

        time.sleep(5)

        for dev in devices:
           device_ip = dev.get("IP")
           device_port = dev.get("PORTA ENVIO TCP")
        
           change_device_state(device_ip, device_port, "1")

        time.sleep(5)

if __name__ == "__main__":
    main()