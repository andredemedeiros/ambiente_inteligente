import socket
import threading

def receive_data(client_socket):
    """
    Thread dedicada para receber dados do gateway.
    """
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if data:
                print(f"\n[DADOS DO SENSOR]: {data}")
        except Exception as e:
            print(f"[ERRO] Erro ao receber dados: {e}")
            break

def send_commands(client_socket):
    """
    Thread dedicada para enviar comandos ao gateway.
    """
    while True:
        try:
            command = input(
                "Opções de comando:\n"
                "- SET_STATE BLOCO (1-ON/0-OFF)\n"
                "- RECIEVE_DATA\n"
                "- LIST\n"
                )
            if command:
                client_socket.sendall(command.encode('utf-8'))

            
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
