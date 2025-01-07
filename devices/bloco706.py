import socket
import struct
import paho.mqtt.client as paho
from paho import mqtt
import json
import time
import threading
from utils import load_env

env = load_env()

power_on = 1
send_time = 0

# Função para enviar mensagem multicast
def send_multicast():
    MCAST_GRP = '228.0.0.8'
    MCAST_PORT = 6789
    msg = '706'

    # Criação do socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Definindo o TTL para o pacote multicast (valor padrão 1 significa "só na rede local")
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Enviar a mensagem multicast
    sock.sendto(msg.encode('utf-8'), (MCAST_GRP, MCAST_PORT))
    print(f'Mensagem enviada para {MCAST_GRP}:{MCAST_PORT}.')

    sock.close()

# Função que roda o servidor TCP
def tcp_server():
    global power_on
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', 40706))  # Escuta na porta 12345
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

        sensor_data = {
            "Tensao": [0, 0, 0],
            "Corrente": [0, 0, 0],
            "Potencia": [0, 0, 0],
        }

        if power_on == 1:
            sensor_data = json.loads(str(msg.payload.decode('utf-8')))

        send_udp_data(sensor_data)

        send_time = time.time()

# Função para enviar os dados de sensor por UDP
def send_udp_data(sensor_data):
    UDP_IP = "127.0.0.1"  # Endereço do cliente UDP (alterar para o IP real)
    UDP_PORT = 12345      # Porta UDP para enviar os dados

    # Converte os dados de sensor para string e depois para bytes
    message = json.dumps(sensor_data).encode('utf-8')

    # Criação do socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Enviar os dados para o cliente UDP
    sock.sendto(message, (UDP_IP, UDP_PORT))
    print(f"Dados de sensor enviados para {UDP_IP}:{UDP_PORT}.")
    
    sock.close()

# Função para configurar o cliente MQTT
def setup_mqtt_client():
    client = paho.Client()
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client.username_pw_set(env.ACESS_NAME, env.ACESS_PASSWORD)
    client.connect(env.URL_BROKER, int(env.PORT_BROKER))
    client.on_message = on_message
    client.subscribe("ESP32-2")
    return client

# Função principal
def main():
    # Envia a mensagem multicast para descoberta do dispositivo
    send_multicast()

    # Inicia o servidor TCP em uma thread separada
    server_thread = threading.Thread(target=tcp_server)
    server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    server_thread.start()

    # Configura e começa a rodar o cliente MQTT
    client = setup_mqtt_client()
    client.loop_forever()

# Chama a função principal
if __name__ == "__main__":
    main()
