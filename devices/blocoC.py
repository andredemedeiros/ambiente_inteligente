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

DEVC_IP = env.DEVC_C_IP
DEVC_TCP_PORT = int(env.DEVC_C_TCP_PORT)  # Porta para receber dados UDP de sensores
BUFFER_SIZE = int(env.BUFFER_SIZE)

TIME_RESET_GTW = int(env.TIME_RESET_GTW)

power_on = 1
send_time = 0

gateways = []

def send_multicast_device():

    MCAST_MSG = {
        'TIPO': "DEVICE",
        'BLOCO': "C",
        'IP': DEVC_IP, 
        'PORTA ENVIO TCP': DEVC_TCP_PORT
    }

    # Criação do socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Definindo o TTL para o pacote multicast (valor padrão 1 significa "só na rede local")
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Loop para enviar a mensagem periodicamente
    print(f'Enviando mensagens via multicast ({MCAST_GRP}:{MCAST_PORT}).')
    while True:
        try:
            # Serializando a mensagem para JSON antes de enviar
            message_mcast = json.dumps(MCAST_MSG)

            # Enviar a mensagem multicast
            sock.sendto(message_mcast.encode('utf-8'), (MCAST_GRP, MCAST_PORT))
          
            # Aguardar o próximo envio (intervalo de 5 segundos, por exemplo)
            time.sleep(5)

        except Exception as e:
            print(f"Erro ao enviar a mensagem: {e}")
            break

    sock.close()

# Função para descobrir dispositivos via multicast UDP
def discover_gtws():
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

            # Verifica se é do tipo "GTW"
            if data_json["TIPO"] == "GTW":
                
                # Verificar se o gtw já foi adicionado à lista de dispositivos
                gtw_id = data_json.get("GTW ID")
                gtw_ip = data_json.get("IP")  # Extraímos o IP do dispositivo
                gtw_port = data_json.get("PORTA ENVIO UDP")

                achou = 0
                # Atualizar o gtw existente com o novo IP e porta
                for gtw in gateways:
                    if gtw['GTW ID'] == gtw_id:
                        achou = 1
                        break

                if achou == 0:
                    gateways.append(data_json)
                    print(f"Novo GTW encontrado: {data_json}")

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
            if data:
                try:
                    power_on = int(data.decode('utf-8'))
                    print(f"Valor de power_on definido em: {power_on}")
                except ValueError:
                    print(f"Dados recebidos inválidos: {data.decode('utf-8')}")
        except Exception as e:
            print(f"Erro ao receber dados: {e}")
        finally:
            client_socket.close()

# Função para enviar os dados de sensor para os GTW'S por UDP
def send_udp_data():
    global power_on

    while True:
        if power_on == 0:
            sensor_data = {'Tensao': [0, 0, 0], 
                            'Corrente': [0, 0, 0], 
                            'Potencia': [0, 0, 0], 
                            'Energia': [0, 0, 0], 
                            'FatorPot': [0, 0, 0],
                            'Bloco': "C",
                            'Estado': power_on}

        else:
            sensor_data = {'Tensao': [random.randint(0, 220), random.randint(0, 220), random.randint(0, 220)], 
                        'Corrente': [random.randint(0, 15), random.randint(0, 15), random.randint(0, 15)], 
                        'Potencia': [random.randint(0, 1000), random.randint(0, 1000), random.randint(0, 1000)], 
                        'Energia': [random.randint(0, 150), random.randint(0, 150), random.randint(0, 150)], 
                        'FatorPot': [random.random(), random.random(), random.random()],
                        'Bloco': "C",
                        'Estado': power_on}
            
        # Converte os dados de sensor para string e depois para bytes
        message_sensor = json.dumps(sensor_data).encode('utf-8')

        # Criação do socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for gtw in gateways:
            gtw_ip = gtw.get("IP")  # Endereço do cliente UDP (alterar para o IP real)
            gte_send_udp_port = int(gtw.get("PORTA ENVIO UDP"))      # Porta UDP para enviar os dados
            
            # Enviar os dados para o cliente UDP
            sock.sendto(message_sensor, (gtw_ip, gte_send_udp_port))
            print(f"Dados do sensor do bloco 706 enviados para {gtw}.")
            
            sock.close()
        
        time.sleep(5)

# Função para esvaziar a lista de gateways a cada 30 segundos
def clear_gateways_list():
    while True:
        time.sleep(TIME_RESET_GTW)  # Espera 30 segundos
        global gateways
        gateways.clear()  # Esvazia a lista de gateways
        print("Lista de gateways esvaziada.")

def main():

    # Thread de apresentação como dispositivo ao grupo multicast 
    send_multicast_device_thread = threading.Thread(target=send_multicast_device)
    send_multicast_device_thread.daemon = True
    send_multicast_device_thread.start()

    # Thread que armazena os GTW via multicast UDP
    recv_multicast_device_thread = threading.Thread(target=discover_gtws)
    recv_multicast_device_thread.daemon = True
    recv_multicast_device_thread.start()

    # Thread para limpar a lista de gateways a cada 30 segundos
    clear_gateways_thread = threading.Thread(target=clear_gateways_list)
    clear_gateways_thread.daemon = True
    clear_gateways_thread.start()

    # Thread para receber dados do GTW
    server_thread = threading.Thread(target=tcp_server)
    server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    server_thread.start()

    # Thread para enviar dados ao GTW
    server_thread = threading.Thread(target=send_udp_data)
    server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    server_thread.start()

    while True:
        time.sleep(1)

# Chama a função principal
if __name__ == "__main__":
    main()
