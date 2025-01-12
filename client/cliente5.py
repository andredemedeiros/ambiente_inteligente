import socket
import threading

import messages_pb2

def receive_data(client_socket):
    """
    Thread dedicada para receber dados do gateway.
    """
    while True:
        try:
            data = client_socket.recv(1024)
            if data:
                # Desserializa os dados usando Protobuf
                sensor_data = messages_pb2.SensorDataCollection()
                sensor_data.ParseFromString(data)
                print(f"\n================= [DADOS DOS SENSORES] ================== \n {sensor_data}")
        except Exception as e:
            print(f"[ERRO] Erro ao receber dados: {e}")
            break

def send_commands(client_socket):
    """
    Thread dedicada para enviar comandos ao gateway usando Protobuf.
    """
    while True:
        try:
            command = input(
                "\n\nOpções de comando:\n"
                "- SET_STATE BLOCO (1-ON/0-OFF)\n"
                "- RECIEVE_DATA\n"
                )

            # Cria a mensagem Command
            command_msg = messages_pb2.Command()

            if command == "RECIEVE_DATA":
                command_msg.type = messages_pb2.Command.RECIEVE_DATA
                command_msg.block_id = "999"
                command_msg.state = bool(int(1))  # Converte 1 ou 0 para booleano
                print("aaaaaaaaaaaaaaaaaaaaaa")
                client_socket.sendall(command_msg.SerializeToString())

            elif command.startswith("SET_STATE"):
                _, block, state = command.split()
                command_msg.type = messages_pb2.Command.SET_STATE
                command_msg.block_id = block
                command_msg.state = bool(int(state))  # Converte 1 ou 0 para booleano
                print("BBBBBBBBBBBBBBBBBB")
                client_socket.sendall(command_msg.SerializeToString())


        except Exception as e:
            print(f"[ERRO] Erro ao enviar comando: {e}")
            break

def main():
    server_ip = "127.0.0.1"  # Substitua pelo IP do gateway
    server_port = 6000

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, server_port))
        print(f"Conectado ao gateway {server_ip}:{server_port}")
    except Exception as e:
        print(f"[ERRO] Não foi possível conectar ao gateway: {e}")
        return

    # Cria threads separadas para envio e recepção
    receive_thread = threading.Thread(target=receive_data, args=(client_socket,))
    send_thread = threading.Thread(target=send_commands, args=(client_socket,))

    receive_thread.daemon = True
    send_thread.daemon = True

    # Inicia ambas as threads
    receive_thread.start()
    send_thread.start()

    # Mantém o cliente rodando até que as threads terminem
    receive_thread.join()
    send_thread.join()

if __name__ == "__main__":
    main()
