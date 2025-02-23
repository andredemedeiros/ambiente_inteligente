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
    global Lista_ip_porta  # Para armazenar a lista de dispositivos

    while True:
        try:
            command = input(
                "\n\nOpções de comando:\n"
                "- SET_STATE BLOCO (ON/OFF)\n"
                "- CHECK_STATE BLOCO\n"
                "- RECEIVE_DATA\n"
                "- LIST\n\n"
            ).strip()

            command_msg = messages_pb2.Command()  # Criar mensagem do tipo Command

            if command == "RECEIVE_DATA":
                # Envia o comando para receber dados de todos os sensores
                command_msg.receive_data.CopyFrom(messages_pb2.ReceiveData())  
                client_socket.sendall(command_msg.SerializeToString())

                try:
                    data = client_socket.recv(1024)
                    if data:
                        sensor_data = messages_pb2.SensorDataCollection()
                        sensor_data.ParseFromString(data)
                        print("\n========= [DADOS DOS SENSORES] =========")
                        for sensor in sensor_data.sensor_data:
                            print(f"\nBloco: {sensor.Bloco}")
                            print(f"  Tensao: {sensor.Tensao}")
                            print(f"  Corrente: {sensor.Corrente}")
                            print(f"  Potencia: {sensor.Potencia}")
                            print(f"  Energia: {sensor.Energia}")
                            print(f"  FatorPot: {sensor.FatorPot}")
                        print("=========================================")

                except Exception as e:
                    print(f"[ERRO] Erro ao receber dados: {e}")
                    break

            elif command.startswith("SET_STATE"):  # Usando gRPC
                _, block, state_str = command.split()
                state = state_str.upper() == "ON"

                command_msg.set_state.block_id = block
                command_msg.set_state.state = state
                client_socket.sendall(command_msg.SerializeToString())

                print(f"[INFO] Comando SET_STATE enviado para {block} ({'ON' if state else 'OFF'})")

            elif command.startswith("CHECK_STATE"):  # Usando gRPC
                _, block = command.split()

                command_msg.check_state.block_id = block
                client_socket.sendall(command_msg.SerializeToString())

                print(f"[INFO] Comando CHECK_STATE enviado para {block}")

            elif command == "LIST":
                command_msg.list.CopyFrom(messages_pb2.List())  
                client_socket.sendall(command_msg.SerializeToString())

                # Aguardando a resposta do servidor
                data = client_socket.recv(1024)
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
                print(f"[INFO] Lista de dispositivos recebida: {Lista_ip_porta}")

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