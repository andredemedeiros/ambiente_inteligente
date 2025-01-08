import socket
import struct
import json
import time
import threading
import box

from dotenv import dotenv_values

import paho.mqtt.client as paho
from paho import mqtt

# Configurações
env = box.Box(dotenv_values(".env"))

MCAST_GRP = env.MCAST_GRP
MCAST_PORT = int(env.MCAST_PORT)

power_on = 1
send_time = 0


def send_multicast(bloc: str = "706", env: dict = []) -> None:
    

    MCAST_MSG = {
        'TIPO': "DEVICE",
        'BLOCO': 706,
        'IP': "127.0.0.1", 
        'PORTA ENVIO TCP': 40706
    }


    # Criação do socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Definindo o TTL para o pacote multicast (valor padrão 1 significa "só na rede local")
    ttl = struct.pack('b', 5)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Enviar a mensagem multicast
    sock.sendto(json.dumps(MCAST_MSG).encode('utf-8'), (MCAST_GRP, int(MCAST_PORT)))
    print(f'Mensagem enviada para {MCAST_GRP}:{MCAST_PORT}.')

    sock.close()

def tcp_server(bloc: str = "706", env: dict = []) -> None:
    global power_on

    if bloc == "706":
        TCP_PORT = env.TCP_PORT_706
    else:
        TCP_PORT = env.TCP_PORT_727
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', int(TCP_PORT)))  # Escuta na porta 40706 ou 40727
    server_socket.listen(1)
    
    print("Servidor TCP aguardando conexão...")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Conexão de {addr}")
        
        try:
            data = client_socket.recv(1024)  # Recebe dados do cliente
            if data:
                try:
                    power_on = int(data.decode('utf-8'))
                    print(f"Valor de power_on atualizado para: {power_on}")
                except ValueError:
                    print(f"Dados recebidos inválidos: {data.decode('utf-8')}")
        except Exception as e:
            print(f"Erro ao receber dados: {e}")
        finally:
            client_socket.close()


# Função callback do MQTT
def on_message(client, userdata, msg):
    global send_time, power_on

    if time.time() - send_time >= int(env.TIME_SAMPLE):

        sensor_data = {'Tensao': [0, 0, 0], 
                       'Corrente': [0, 0, 0], 
                       'Potencia': [0, 0, 0], 
                       'Energia': [0, 0, 0], 
                       'FatorPot': [0, 0, 0],
                       'Bloco': "706",
                       'Estado': power_on}

        if power_on == 1:
            sensor_data = json.loads(str(msg.payload.decode('utf-8')))
            sensor_data['Bloco'] = "706"  # Garante que o campo 'Bloco' sempre estará presente
            sensor_data['Estado'] = power_on

        send_udp_data(sensor_data)

        send_time = time.time()

# Função para enviar os dados de sensor por UDP
def send_udp_data(sensor_data):
    UDP_IP = env.GTW_IP  # Endereço do cliente UDP (alterar para o IP real)
    UDP_PORT = env.GTW_UDP_PORT      # Porta UDP para enviar os dados

    # Converte os dados de sensor para string e depois para bytes
    message = json.dumps(sensor_data).encode('utf-8')

    # Criação do socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Enviar os dados para o cliente UDP
    sock.sendto(message, (UDP_IP, int(UDP_PORT)))
    print(f"Dados de sensor enviados para {UDP_IP}:{UDP_PORT}.")
    
    sock.close()

# Função para configurar o cliente MQTT
def setup_mqtt_client(bloc: str = "706", env: dict = []) -> paho.Client:
    
    if bloc == "706":
        TOPIC_DEVIC = env.TOPIC_DEVICE_706
    else:
        TOPIC_DEVIC = env.TOPIC_DEVICE_727

    client = paho.Client()
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client.username_pw_set(env.ACESS_NAME, env.ACESS_PASSWORD)
    client.connect(env.URL_BROKER, int(env.PORT_BROKER))
    client.on_message = on_message
    client.subscribe(TOPIC_DEVIC)
    return client


def main():

    send_multicast(bloc="706", env=env)

    server_thread = threading.Thread(target=tcp_server, args=("706", env))
    server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    server_thread.start()

    # Configura e começa a rodar o cliente MQTT
    client = setup_mqtt_client(bloc="706", env=env)
    client.loop_forever()

# Chama a função principal
if __name__ == "__main__":
    main()
