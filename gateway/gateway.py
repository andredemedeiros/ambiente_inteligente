import socket
import struct
import threading
import time
import box
from dotenv import dotenv_values
import json
import grpc
import messages_pb2
import sensor_pb2
import sensor_pb2_grpc

# Configurações
env = box.Box(dotenv_values(".env"))

MCAST_GRP = env.MCAST_GRP
MCAST_PORT = int(env.MCAST_PORT)
GTW_IP = env.GTW_IP
GTW_UDP_PORT = int(env.GTW_UDP_PORT)  # Porta para receber dados UDP de sensores
BUFFER_SIZE = int(env.BUFFER_SIZE)
TCP_PORT = 6000  # Porta TCP para comunicação com o cliente

devices = []  # Lista de dispositivos disponíveis via multicast UDP {'TIPO': 'DEVICE', 'BLOCO': 'C', 'IP': '127.0.0.1', 'PORTA ENVIO TCP': 50002}
sensor_data_queue = []  # Fila para armazenar dados de sensores
recent_sensor_data = {}
recent_sensor_data_lock = threading.Lock()

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
    global recent_sensor_data
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', GTW_UDP_PORT))

    # Dicionário para rastrear o último tempo de recebimento de dados de cada sensor
    last_received_time = {}

    def check_timeout():
        while True:
            time.sleep(10)  # Verifica a cada 10 segundos
            current_time = time.time()
            with recent_sensor_data_lock:
                for block_id, last_time in list(last_received_time.items()):
                    if current_time - last_time > 20:  # Timeout de 20 segundos
                        print(f"[INFO] Sensor do bloco {block_id} excedeu o timeout. Removendo da lista.")
                        # Remove o sensor da lista de dispositivos conectados
                        devices[:] = [dev for dev in devices if dev['BLOCO'] != block_id]
                        # Remove o sensor do dicionário de últimos tempos
                        del last_received_time[block_id]
                        # Remove o sensor do dicionário de dados recentes
                        if block_id in recent_sensor_data:
                            del recent_sensor_data[block_id]

    # Inicia a thread para verificar o timeout
    timeout_thread = threading.Thread(target=check_timeout, daemon=True)
    timeout_thread.start()

    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            print(f"[DEBUG] Dados brutos recebidos: {data}")

            # Desserializa os dados usando Protobuf
            sensor_data = messages_pb2.SensorData()
            sensor_data.ParseFromString(data)

            print(f"[DEBUG] Dados decodificados: {sensor_data}")

            block_id = sensor_data.Bloco
            if block_id is None:
                print(f"[DEBUG] Dados recebidos sem 'Bloco': {sensor_data}")
                continue

            # Atualiza o último tempo de recebimento de dados do sensor
            last_received_time[block_id] = time.time()

            # Atualiza o dado mais recente no vetor global protegido por Lock
            with recent_sensor_data_lock:
                recent_sensor_data[block_id] = sensor_data

            # Adiciona à fila de dados recebidos
            sensor_data_queue.append(sensor_data)
            print(devices)
        except Exception as e:
            print(f"[ERRO] Erro ao receber dados UDP: {e}")

def tcp_server():    #Ainda usado entre o cliente e o gateway
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
            # Recebe o comando do cliente
            command_data = client_socket.recv(1024)
            if not command_data:
                break

            # Desserializa o comando recebido
            command_msg = messages_pb2.Command()
            command_msg.ParseFromString(command_data)
            print(command_msg)

            # Processa o comando baseado no tipo
            if command_msg.type == messages_pb2.Command.RECIEVE_DATA:
                with recent_sensor_data_lock:
                    # Cria uma SensorDataCollection para segurar todos os dados do sensor
                    sensor_data_collection = messages_pb2.SensorDataCollection()

                    # Loop através dos dados dos sensores recentes e adiciona-os à coleção
                    for block_id, sensor_data in recent_sensor_data.items():
                        # Adiciona os dados do sensor à coleção
                        sensor_data_collection.sensor_data.append(sensor_data)

                    # Serializa os dados para uma string de bytes
                    serialized_data = sensor_data_collection.SerializeToString()

                # Envia os dados serializados ao cliente
                print(f"[DEBUG] Dados enviados ao cliente: {len(serialized_data)} bytes")
                client_socket.sendall(serialized_data)

            elif command_msg.type == messages_pb2.Command.SET_STATE:  #USANDO GRPC
                block_id = command_msg.block_id
                state = "on" if command_msg.state else "off"
                for dev in devices:
                    if dev["BLOCO"] == block_id:
                        ip_porta = dev["IP"] + ':' + str(dev["PORTA ENVIO TCP"])
                        
                        channel = grpc.insecure_channel(ip_porta)
                        stub = sensor_pb2_grpc.SensorControlStub(channel)
                        request = sensor_pb2.CommandRequest(command=state)
                        response = stub.SendCommand(request)
                        print(f"Resposta do Servidor gRPC: {response.message}")

            elif command_msg.type == messages_pb2.Command.LIST:
                # Responde ao comando LIST com a lista de dispositivos
                device_list = messages_pb2.DeviceList()

                # Preenche a lista com os dispositivos conectados
                for dev in devices:
                    device_info = messages_pb2.DeviceInfo(
                        TIPO="DEVICE",  # A informação 'TIPO' está sendo enviada como 'DEVICE'
                        BLOCO=dev["BLOCO"],
                        IP=dev["IP"],
                        PORTA_ENVIO_TCP=dev["PORTA ENVIO TCP"]
                    )
                    device_list.devices.append(device_info)

                # Serializa os dados da lista
                serialized_data = device_list.SerializeToString()
                print(f"[DEBUG] Lista de dispositivos enviada ao cliente ({len(serialized_data)} bytes).")
                client_socket.sendall(serialized_data)

            elif command_msg.type == messages_pb2.Command.CHECK_STATE:  #usando GRPC
                block_id = command_msg.block_id
                for dev in devices:
                    if dev["BLOCO"] == block_id:
                        ip_porta = dev["IP"] + ':' + str(dev["PORTA ENVIO TCP"])
                        
                        channel = grpc.insecure_channel(ip_porta)
                        stub = sensor_pb2_grpc.SensorControlStub(channel)
                        request = sensor_pb2.CommandRequest(command="check")
                        response = stub.SendCommand(request)
                        print(f"Resposta do Servidor gRPC: {response.message}")

    except Exception as e:
        print(f"[ERRO] Erro ao processar a requisição: {e}")
        client_socket.close()

# def change_device_state(device_bloc, device_ip, device_port, state):
#     """
#     Envia o estado atualizado para um dispositivo usando Protobuf.
#     """
#     try:
#         # Cria a mensagem StateChange e preenche com o novo estado
#         state_change_msg = messages_pb2.StateChange()
#         state_change_msg.new_state = state

#         # Serializa a mensagem para um formato binário
#         serialized_state = state_change_msg.SerializeToString()

#         # Conecta ao dispositivo e envia a mensagem serializada
#         tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         tcp_socket.settimeout(10)
#         tcp_socket.connect((device_ip, int(device_port)))
#         tcp_socket.sendall(serialized_state)

#         print(f"[INFO] Estado {state} enviado para bloco {device_bloc} ({len(serialized_state)} bytes).")
#     except (socket.timeout, socket.error) as e:
#         print(f"[ERRO] Falha na conexão TCP com {device_ip}:{device_port}: {e}")
#         # Remove o dispositivo da lista em caso de erro de conexão
#         devices[:] = [dev for dev in devices if not (dev['IP'] == device_ip and dev['PORTA ENVIO TCP'] == device_port)]
#     finally:
#         tcp_socket.close()


def main():
    threading.Thread(target=send_multicast_gtw, daemon=True).start()
    threading.Thread(target=discover_devices, daemon=True).start()
    threading.Thread(target=listen_for_sensor_data, daemon=True).start()
    threading.Thread(target=tcp_server, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
