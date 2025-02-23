import socket
import threading
import time
import messages_pb2
import sensor_pb2
import sensor_pb2_grpc
import grpc

RECONNECT_INTERVAL = 10  # Intervalo em segundos para tentar reconectar

Lista_ip_porta = []  # Inicialmente vazia, será preenchida pela resposta do LIST


# def receive_data(client_socket):
#     """
#     Thread dedicada para receber dados do gateway.
#     """
#     while True:
#         try:
#             data = client_socket.recv(1024)
#             if data:
#                 # Desserializa os dados usando Protobuf
#                 sensor_data = messages_pb2.SensorDataCollection()
#                 sensor_data.ParseFromString(data)
#                 print(f"\n================= [DADOS DOS SENSORES] ==================\n{sensor_data}")
#         except Exception as e:
#             print(f"[ERRO] Erro ao receber dados: {e}")
#             break


def update_ip_porta_list(data):
    """
    Atualiza a lista de IPs e portas com a resposta do comando LIST.
    """
    global Lista_ip_porta
    try:
        # Aqui, vamos supor que a resposta seja uma lista de blocos com IPs e portas.
        # Parse a resposta e atualize Lista_ip_porta.
        # Isso vai depender de como o seu Protobuf está estruturado, mas um exemplo seria:
        
        block_list = sensor_pb2.BlockList()  # Supondo que você tenha uma estrutura chamada BlockList no seu Protobuf
        block_list.ParseFromString(data)

        Lista_ip_porta = []
        for block in block_list.blocks:
            Lista_ip_porta.append({
                'TIPO': 'DEVICE',
                'BLOCO': block.block_id,
                'IP': block.ip,
                'PORTA ENVIO TCP': block.port
            })

        print(f"Lista de dispositivos atualizada: {Lista_ip_porta}")
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar lista de IPs e portas: {e}")


def send_commands(client_socket):
    """
    Thread dedicada para enviar comandos ao gateway usando Protobuf.
    """
    global Lista_ip_porta  # Vamos usar essa variável para armazenar a lista de dispositivos

    while True:
        try:
            command = input(
                "\n\nOpções de comando:\n"
                "- SET_STATE BLOCO (ON/OFF)\n"
                "- CHECK_STATE BLOCO\n"
                "- RECIEVE_DATA\n"
                "- LIST\n\n"
            )

            # Cria a mensagem Command
            command_msg = messages_pb2.Command()

            if command == "RECIEVE_DATA":
                # Envia o comando para receber dados de todos os sensores
                command_msg.type = messages_pb2.Command.RECIEVE_DATA
                command_msg.block_id = "999"  # Apenas um valor placeholder
                command_msg.state = bool(int(1))  # Apenas para preencher o campo state
                client_socket.sendall(command_msg.SerializeToString())

                try:
                    data = client_socket.recv(1024)
                    if data:
                        # Desserializa os dados usando Protobuf
                        sensor_data = messages_pb2.SensorDataCollection()
                        sensor_data.ParseFromString(data)
                        print("\n=========================== [DADOS DOS SENSORES] ==============================")
                        for i in range(0, len(sensor_data.sensor_data), 3):  # Agrupar os dados a cada 3 elementos
                            sensor_group = sensor_data.sensor_data[i:i+3]
                            
                            print(f"Bloco: {sensor_group[0].Bloco}")
                            for idx, sensor in enumerate(sensor_group):
                                print(f"\nBloco: {sensor.Bloco}")
                                print(f"  Tensao: {sensor.Tensao}")
                                print(f"  Corrente: {sensor.Corrente}")
                                print(f"  Potencia: {sensor.Potencia}")
                                print(f"  Energia: {sensor.Energia}")
                                print(f"  FatorPot: {sensor.FatorPot}")
                        print("================================================================================")

                except Exception as e:
                    print(f"[ERRO] Erro ao receber dados: {e}")
                    break

            elif command.startswith("SET_STATE"):  # Modificado para utilizar gRPC
                # _, block, state = command.split()
                # for device in Lista_ip_porta:
                #     if device["BLOCO"] == block:
                #         ip_porta = device["IP"] + ':' + str(device["PORTA ENVIO TCP"])
                        
                #         channel = grpc.insecure_channel(ip_porta)
                #         stub = sensor_pb2_grpc.SensorControlStub(channel)
                #         request = sensor_pb2.CommandRequest(command=state)
                #         response = stub.SendCommand(request)
                #         print(f"Resposta do Servidor gRPC: {response.message}")
                command_msg.type = messages_pb2.Command.SET_STATE
                command_msg.block_id = "999"  # Apenas um valor placeholder
                command_msg.state = bool(int(1))  # Apenas para preencher o campo state
                client_socket.sendall(command_msg.SerializeToString())

                # Aguardando a resposta do servidor
                data = client_socket.recv(1024)  # Espera pela resposta com a lista de dispositivos
                device_list = messages_pb2.DeviceList()
                device_list.ParseFromString(data)


            elif command.startswith("CHECK_STATE"):  # Modificado para utilizar gRPC
                _, block = command.split()
                for device in Lista_ip_porta:
                    if device["BLOCO"] == block:
                        ip_porta = device["IP"] + ':' + str(device["PORTA ENVIO TCP"])
                        
                        channel = grpc.insecure_channel(ip_porta)
                        stub = sensor_pb2_grpc.SensorControlStub(channel)
                        request = sensor_pb2.CommandRequest(command="check")
                        response = stub.SendCommand(request)
                        print(f"Resposta do Servidor gRPC: {response.message}")

            elif command == "LIST":
                # Envia o comando LIST para o servidor
                command_msg.type = messages_pb2.Command.LIST
                command_msg.block_id = "999"  # Apenas um valor placeholder
                command_msg.state = bool(int(1))  # Apenas para preencher o campo state
                client_socket.sendall(command_msg.SerializeToString())

                # Aguardando a resposta do servidor
                data = client_socket.recv(1024)  # Espera pela resposta com a lista de dispositivos
                device_list = messages_pb2.DeviceList()
                device_list.ParseFromString(data)

                # Atualiza a lista de dispositivos
                Lista_ip_porta = []
                for device in device_list.devices:
                    Lista_ip_porta.append({
                        'TIPO': device.TIPO,
                        'BLOCO': device.BLOCO,
                        'IP': device.IP,
                        'PORTA ENVIO TCP': device.PORTA_ENVIO_TCP
                    })
                print(f"Lista de dispositivos recebida: {Lista_ip_porta}")

        except Exception as e:
            print(f"[ERRO] Erro ao enviar comando: {e}")
            break


def connect_to_gateway(server_ip, server_port):
    """
    Tenta conectar ao gateway e retorna o socket conectado.
    """
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_ip, server_port))
            print(f"Conectado ao gateway {server_ip}:{server_port}")
            return client_socket
        except Exception as e:
            print(f"[ERRO] Não foi possível conectar ao gateway: {e}")
            print(f"Tentando reconectar em {RECONNECT_INTERVAL} segundos...")
            time.sleep(RECONNECT_INTERVAL)


def main():
    server_ip = "127.0.0.1"
    server_port = 6000

    while True:
        client_socket = connect_to_gateway(server_ip, server_port)

        # Cria threads separadas para envio e recepção
        #receive_thread = threading.Thread(target=receive_data, args=(client_socket,))
        send_thread = threading.Thread(target=send_commands, args=(client_socket,))

        #receive_thread.daemon = True
        send_thread.daemon = True

        # Inicia ambas as threads
        #receive_thread.start()
        send_thread.start()

        # Aguarda ambas as threads terminarem
        #receive_thread.join()
        send_thread.join()

        print("[INFO] Conexão perdida. Reiniciando processo de conexão...")

if __name__ == "__main__":
    main()





# A FAZER
# 1 - Criar variável com lista dos sensores e suas repsctivas portas
# 2 - Adaptar a função SET_STATE BLOCO para utilziar o gRPC, utilizando como referência os valores do vetor
# 3 - Adaptar cada disposivo para que eles respondam em portas distintas.
# 4 - Fazer com que esses disposivos enviem a porta pela msg também.