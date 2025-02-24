import socket
import struct
import json
import time
import threading
import box

import random
import grpc
from concurrent import futures
import messages_pb2
from dotenv import dotenv_values

import sensor_pb2
import sensor_pb2_grpc

import paho.mqtt.client as paho
from paho import mqtt
import pika

# Configurações
env = box.Box(dotenv_values(".env"))

MCAST_GRP = env.MCAST_GRP
MCAST_PORT = int(env.MCAST_PORT)

URL_BROKER = env.URL_BROKER
PORT_BROKER = int(env.PORT_BROKER)
ACESS_NAME = env.ACESS_NAME
ACESS_PASSWORD = env.ACESS_PASSWORD

TIME_SAMPLE = int(env.TIME_SAMPLE)

TOPIC_DEVICE = env.TOPIC_DEVICE_706

DEVC_IP = env.DEVC_706_IP
DEVC_TCP_PORT = int(env.DEVC_706_TCP_PORT)  # Porta para receber dados UDP de sensores
BUFFER_SIZE = int(env.BUFFER_SIZE)

TIME_RESET_GTW = int(env.TIME_RESET_GTW)

power_on = 1
send_time = 0

gateways = []

def send_multicast_device():

    MCAST_MSG = {
        'TIPO': "DEVICE",
        'BLOCO': "706",
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

#def tcp_server():
    """
    Servidor TCP para receber comandos do gateway e reagir a eles.
    """
    global power_on  # Variável global para armazenar o estado atual do dispositivo
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', DEVC_TCP_PORT))  # Porta configurada para escutar
    server_socket.listen(1)
    
    print("Servidor TCP disponível e aguardando conexões...")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Conexão recebida de {addr}")
        
        try:
            data = client_socket.recv(1024)  # Recebe dados do cliente
            if data:
                # Desserializa os dados recebidos usando Protobuf
                state_change_msg = messages_pb2.StateChange()
                state_change_msg.ParseFromString(data)
                
                # Processa o estado recebido
                new_state = state_change_msg.new_state
                if new_state.isdigit():
                    power_on = int(new_state)
                    print(f"[INFO] Novo estado recebido: {power_on} (power_on atualizado)")
                else:
                    print(f"[AVISO] Estado recebido inválido: {new_state}")
        except messages_pb2.DecodeError as e:
            print(f"[ERRO] Falha ao desserializar a mensagem Protobuf: {e}")
        except Exception as e:
            print(f"[ERRO] Erro ao processar dados recebidos: {e}")
        finally:
            client_socket.close()

# Função callback do MQTT
def on_message(client, userdata, msg):
    global send_time, power_on

    if time.time() - send_time >= TIME_SAMPLE:
        sensor_data = messages_pb2.SensorData()
        sensor_data.Bloco = "706"
        sensor_data.Estado = power_on

        if power_on == 0:
            sensor_data.Tensao.extend([0.0, 0.0, 0.0])
            sensor_data.Corrente.extend([0.0, 0.0, 0.0])
            sensor_data.Potencia.extend([0.0, 0.0, 0.0])
            sensor_data.Energia.extend([0.0, 0.0, 0.0])
            sensor_data.FatorPot.extend([0.0, 0.0, 0.0])

        else:
            Tensao = json.loads(str(msg.payload.decode('utf-8'))).get("Tensao")
            Corrente = json.loads(str(msg.payload.decode('utf-8'))).get("Corrente")
            Potencia = json.loads(str(msg.payload.decode('utf-8'))).get("Potencia")
            Energia = json.loads(str(msg.payload.decode('utf-8'))).get("Energia")
            FatorPot = json.loads(str(msg.payload.decode('utf-8'))).get("FatorPot")
            print(Tensao)
            type(Tensao)
            sensor_data.Tensao.extend(Tensao)
            sensor_data.Corrente.extend(Corrente)
            sensor_data.Potencia.extend(Potencia)
            sensor_data.Energia.extend(Energia)
            sensor_data.FatorPot.extend(FatorPot)

        # Converte para bytes usando Protobuf
        message_sensor = sensor_data.SerializeToString()

        channel.basic_publish(
            exchange="sensors_exchange",
            routing_key="",
            body=message_sensor,
            properties=pika.BasicProperties(
                delivery_mode=2 # mensagem persistente em caso de reinicialização do broker
            )
        )
        print(f"Dados do sensor enviados para o broker.")
        time.sleep(5)

class SensorControlServicer(sensor_pb2_grpc.SensorControlServicer):
    def SendCommand(self, request, context):
        global power_on
        command = request.command.lower()
        if command == "on":
            power_on = 1
            response_message = "Sensor ligado com sucesso!"
        elif command == "off":
            power_on = 0
            response_message = "Sensor desligado com sucesso!"

        elif command == "check":
            if power_on == 1:
                response_message = "O sensor está ativo"
            else:
                response_message = "O sensor está inativo"

        else:
            response_message = "Comando inválido!"
        print(f"Recebido: {request.command} -> Resposta: {response_message}")
        return sensor_pb2.CommandResponse(message=response_message)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorControlServicer_to_server(SensorControlServicer(), server)
    server.add_insecure_port(f"[::]:{DEVC_TCP_PORT}")
    server.start()
    print(f"Servidor gRPC rodando na porta {DEVC_TCP_PORT}...")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)
        print("Servidor encerrado.")

# Função para configurar o cliente MQTT
def setup_mqtt_client():

    client = paho.Client()
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client.username_pw_set(ACESS_NAME, ACESS_PASSWORD)
    client.connect(URL_BROKER, PORT_BROKER)
    client.on_message = on_message
    client.subscribe(TOPIC_DEVICE)
    return client

# Função para esvaziar a lista de gateways a cada 30 segundos
def clear_gateways_list():
    while True:
        time.sleep(TIME_RESET_GTW)  # Espera 30 segundos
        global gateways
        gateways.clear()  # Esvazia a lista de gateways
        print("Lista de gateways esvaziada.")

def set_broker_channel():
    connection_parameters = pika.ConnectionParameters(
        host="localhost",
        port=5672,
        credentials=pika.PlainCredentials(
            username="test",
            password="test"
            )
        )

    return pika.BlockingConnection(connection_parameters).channel()

channel = set_broker_channel()

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
    #server_thread = threading.Thread(target=tcp_server)
    #server_thread.daemon = True  # Faz com que a thread seja encerrada quando o programa principal for encerrado
    #server_thread.start()

    # Configura e começa a rodar o cliente MQTT
    client = setup_mqtt_client()
    client.loop_forever()

    #Thread para o servidor GRPC
    threading.Thread(target=serve, daemon=True).start()

# Chama a função principal
if __name__ == "__main__":
    main()
