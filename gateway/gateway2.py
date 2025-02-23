import socket
import struct
import threading
import time
import box
from dotenv import dotenv_values
import json
import grpc
import uvicorn
import messages_pb2
import sensor_pb2
import sensor_pb2_grpc
from fastapi import FastAPI, HTTPException
from google.protobuf.json_format import MessageToDict
import pika


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

    # Dicionário para rastrear o último tempo de recebimento de dados de cada sensor
    last_received_time = {}

    # Definindo a função de callback antes de usá-la
    def minha_callback(ch, method, properties, body):
        try:
            sensor_data = messages_pb2.SensorData()
            sensor_data.ParseFromString(body)

            print(f"[DEBUG] Dados decodificados: {sensor_data}")

            block_id = sensor_data.Bloco
            if block_id is None:
                print(f"[DEBUG] Dados recebidos sem 'Bloco': {sensor_data}")
                return

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

    # Configura a conexão com o RabbitMQ
    connection_parameters = pika.ConnectionParameters(
        host="localhost",
        port=5672,
        credentials=pika.PlainCredentials(
            username="test",
            password="test"
        )
    )
    
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()

    channel.queue_declare(
        queue="sensors_queue",
        durable=True,
        arguments={
            'x-message-ttl': 30000  # Tempo de vida da mensagem
        }
    )

    # Função para escutar os dados da fila RabbitMQ
    def start_consuming():
        channel.basic_consume(
            queue="sensors_queue",
            auto_ack=True,
            on_message_callback=minha_callback
        )

        print(f'Listening to RabbitMQ on Port 5672')
        channel.start_consuming()

    # Inicia a thread para o RabbitMQ
    consume_thread = threading.Thread(target=start_consuming, daemon=True)
    consume_thread.start()

    # Inicia a thread para verificar o timeout
    timeout_thread = threading.Thread(target=check_timeout, daemon=True)
    timeout_thread.start()

    # Mantém a função ativa indefinidamente
    while True:
        time.sleep(1)  # O loop de espera mantém a função ativa para as threads


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
            # Recebe os dados do cliente
            command_data = client_socket.recv(1024)
            if not command_data:
                break

            # Desserializa a mensagem recebida
            command_msg = messages_pb2.Command()
            command_msg.ParseFromString(command_data)
            print(f"[DEBUG] Comando recebido: {command_msg}")

            # Identifica qual comando foi enviado usando `WhichOneof`
            command_type = command_msg.WhichOneof("payload")

            if command_type == "receive_data":
                with recent_sensor_data_lock:
                    sensor_data_collection = messages_pb2.SensorDataCollection()

                    # Adiciona os dados dos sensores à coleção
                    for block_id, sensor_data in recent_sensor_data.items():
                        sensor_data_collection.sensor_data.append(sensor_data)

                    serialized_data = sensor_data_collection.SerializeToString()

                # Envia os dados ao cliente
                print(f"[DEBUG] Dados enviados ao cliente: {len(serialized_data)} bytes")
                client_socket.sendall(serialized_data)

            elif command_type == "set_state":  # Usando gRPC
                block_id = command_msg.set_state.block_id
                state = "on" if command_msg.set_state.state else "off"

                for dev in devices:
                    if dev["BLOCO"] == block_id:
                        ip_porta = f"{dev['IP']}:{dev['PORTA ENVIO TCP']}"

                        channel = grpc.insecure_channel(ip_porta)
                        stub = sensor_pb2_grpc.SensorControlStub(channel)
                        request = sensor_pb2.CommandRequest(command=state)
                        response = stub.SendCommand(request)
                        print(f"[DEBUG] Resposta do Servidor gRPC: {response.message}")

            elif command_type == "list":
                # Cria a lista de dispositivos
                device_list = messages_pb2.DeviceList()

                for dev in devices:
                    device_info = messages_pb2.DeviceInfo(
                        TIPO="DEVICE",
                        BLOCO=dev["BLOCO"],
                        IP=dev["IP"],
                        PORTA_ENVIO_TCP=dev["PORTA ENVIO TCP"]
                    )
                    device_list.devices.append(device_info)

                serialized_data = device_list.SerializeToString()
                print(f"[DEBUG] Lista de dispositivos enviada ao cliente ({len(serialized_data)} bytes).")
                client_socket.sendall(serialized_data)

            elif command_type == "check_state":  # Usando gRPC
                block_id = command_msg.check_state.block_id

                for dev in devices:
                    if dev["BLOCO"] == block_id:
                        ip_porta = f"{dev['IP']}:{dev['PORTA ENVIO TCP']}"

                        channel = grpc.insecure_channel(ip_porta)
                        stub = sensor_pb2_grpc.SensorControlStub(channel)
                        request = sensor_pb2.CommandRequest(command="check")
                        response = stub.SendCommand(request)
                        print(f"[DEBUG] Resposta do Servidor gRPC: {response.message}")

    except Exception as e:
        print(f"[ERRO] Erro ao processar a requisição: {e}")

    finally:
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


app = FastAPI()

# Endpoint to get sensor data
@app.get("/sensor-data")
def get_sensor_data():
    with recent_sensor_data_lock:
        # Convert Protobuf messages to dictionaries
        sensor_data_dict = {
            block_id: MessageToDict(sensor_data, preserving_proto_field_name=True)
            for block_id, sensor_data in recent_sensor_data.items()
        }
        
        
        return sensor_data_dict

# Endpoint to list connected devices
@app.get("/devices")
def list_devices():
    return devices

# Endpoint to set the state of a device
@app.post("/set-device-state/{block_id}/{state}")
def set_device_state(block_id: str, state: bool):
    # Convert state to "on" or "off"
    state_str = "on" if state else "off"

    # Find the device by block_id
    for dev in devices:
        if dev["BLOCO"] == block_id:
            ip_porta = f"{dev['IP']}:{dev['PORTA ENVIO TCP']}"

            try:
                # Use gRPC to communicate with the sensor
                channel = grpc.insecure_channel(ip_porta)
                stub = sensor_pb2_grpc.SensorControlStub(channel)
                request = sensor_pb2.CommandRequest(command=state_str)
                response = stub.SendCommand(request)
                print(f"[DEBUG] Resposta do Servidor gRPC: {response.message}")

                # Return the response message
                return {
                    "block_id": block_id,
                    "state": state_str,
                    "message": response.message
                }
            except grpc.RpcError as e:
                raise HTTPException(status_code=500, detail=f"gRPC error: {e.details()}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error communicating with sensor: {str(e)}")

    # If the device is not found, return a 404 error
    raise HTTPException(status_code=404, detail=f"No device found with block_id: {block_id}")


# Endpoint to check the state of a device
@app.get("/check-device-state/{block_id}")
def check_device_state(block_id):
    
    for dev in devices:
        if dev["BLOCO"] == block_id:
            sensor_ip = dev["IP"]
            sensor_port = dev["PORTA ENVIO TCP"]
            sensor_address = f"{sensor_ip}:{sensor_port}"

            try:
                # Use gRPC to communicate with the sensor
                channel = grpc.insecure_channel(sensor_address)
                stub = sensor_pb2_grpc.SensorControlStub(channel)
                request = sensor_pb2.CommandRequest(command="check")
                response = stub.SendCommand(request)

                # Return the sensor's state
                return {"block_id": block_id, "state": response.message}
            except grpc.RpcError as e:
                raise HTTPException(status_code=500, detail=f"gRPC error: {e.details()}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error communicating with sensor: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail=f"No device found with block_id: {block_id}")

def run_rest_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def protobuf_to_dict(proto_obj):
    """
    Converts a Protobuf message to a Python dictionary.
    """
    result = {}
    for field in proto_obj.DESCRIPTOR.fields:
        value = getattr(proto_obj, field.name)
        if field.type == field.TYPE_MESSAGE:  # Nested Protobuf message
            if field.label == field.LABEL_REPEATED:  # Repeated field (list)
                result[field.name] = [protobuf_to_dict(item) for item in value]
            else:
                result[field.name] = protobuf_to_dict(value)
        else:  # Scalar field
            result[field.name] = value
    return result


def main():
    threading.Thread(target=send_multicast_gtw, daemon=True).start()
    threading.Thread(target=discover_devices, daemon=True).start()
    threading.Thread(target=listen_for_sensor_data, daemon=True).start()
   # threading.Thread(target=tcp_server, daemon=True).start()
    threading.Thread(target=run_rest_api, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()