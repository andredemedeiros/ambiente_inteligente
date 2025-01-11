import socket
import struct
import json
import time
import threading
import box
import random

from dotenv import dotenv_values


# Configurações
env = box.Box(dotenv_values(".env"))

MCAST_GRP = env.MCAST_GRP
MCAST_PORT = int(env.MCAST_PORT)

TIME_SAMPLE = int(env.TIME_SAMPLE)

DEVC_IP = env.DEVC_LAMP_IP
DEVC_TCP_PORT = int(env.DEVC_LAMP_TCP_PORT)  # Porta para receber dados UDP de sensores
BUFFER_SIZE = int(env.BUFFER_SIZE)

TIME_RESET_GTW = int(env.TIME_RESET_GTW)

power_on = 1
gateway = None

def send_multicast_device():

    MCAST_MSG = {
        'TIPO': "LAMPADA",
        'IP': DEVC_IP, 
        'PORTA ENVIO TCP': DEVC_TCP_PORT,
    }

    # Criação do socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Definindo o TTL para o pacote multicast (valor padrão 1 significa "só na rede local")
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Enviar a mensagem periodicamente
    try:
        # Serializando a mensagem para JSON antes de enviar
        message_mcast = json.dumps(MCAST_MSG)

        # Enviar a mensagem multicast
        sock.sendto(message_mcast.encode('utf-8'), (MCAST_GRP, MCAST_PORT))
        
    except Exception as e:
        print(f"Erro ao enviar a mensagem: {e}")
    
    print(f'Mensagem multicast enviada.')
    sock.close()

# Função para descobrir dispositivos via multicast UDP
def discover_gtws():
    global gateway

    # Cria o socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', MCAST_PORT))

    # Adiciona o socket à lista de multicast
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        try:
            # Aguarda uma mensagem no multicast
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)

            data_json = json.loads(data.decode('utf-8'))

            # Verifica se a mensagem é do gtw
            if data_json["TIPO"] == "GTW":
                
                gateway = data_json

                print(f"GTW atualizado: {data_json}")

                send_multicast_device()

        except socket.timeout:
            continue

def tcp_server():
    global power_on
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', DEVC_TCP_PORT))  # Escuta na porta 50706 ou 50727
    server_socket.listen(1)
    
    print("Socket TCP disponível...")
    
    while True:
        client_socket, addr = server_socket.accept()
        
        try:
            data = client_socket.recv(1024)  # Recebe dados do cliente
            msg = data.decode('utf-8')

            if msg != "ping":
                try:
                    power_on = int(msg)
                    print(f"Valor de power_on definido em: {power_on}")
                except ValueError:
                    print(f"Dados recebidos inválidos: {msg}")
            else:
                print(msg)

        except Exception as e:
            print(f"Erro ao receber dados: {e}")
        finally:
            client_socket.close()

# Função para enviar os dados de sensor para os GTW'S por UDP
def send_udp_data():
    global power_on

    while True:
        sensor_data = {'TIPO': "LAMPADA",'ESTADO': power_on}
            
        # Converte os dados de sensor para string e depois para bytes
        message_sensor = json.dumps(sensor_data).encode('utf-8')

        # Criação do socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if gateway:
            gtw_ip = gateway.get("IP")  # Endereço do cliente UDP (alterar para o IP real)
            gte_send_udp_port = int(gateway.get("PORTA ENVIO UDP"))      # Porta UDP para enviar os dados
            
            # Enviar os dados para o cliente UDP
            sock.sendto(message_sensor, (gtw_ip, gte_send_udp_port))
            print(f"Dados enviados.")
            
            sock.close()
        
        time.sleep(5)

def main():

    # Thread que armazena os GTW via multicast UDP
    recv_multicast_device_thread = threading.Thread(target=discover_gtws)
    recv_multicast_device_thread.daemon = True
    recv_multicast_device_thread.start()

    # Thread para receber dados do GTW
    server_thread = threading.Thread(target=tcp_server)
    server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    server_thread.start()

    # Thread para enviar dados ao GTW
    server_thread = threading.Thread(target=send_udp_data)
    server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    server_thread.start()

    while True:
        time.sleep(TIME_RESET_GTW)
        global gateway
        gateway = None
        print('Limpar gateway')

# Chama a função principal
if __name__ == "__main__":
    main()
