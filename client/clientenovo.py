import socket
import json
import threading

GATEWAY_IP = '127.0.0.1'
GATEWAY_PORT = 6000

# Função para receber dados do gateway
def receive_data(sock):
    try:
        while True:
            data = sock.recv(1024)
            if data:
                print("\n[Dado recebido do gateway]:", data.decode())
            else:
                break
    except Exception as e:
        print(f"Erro ao receber dados do gateway: {e}")

# Função para enviar comandos para o gateway
def send_command(sock, sensor_id, command):
    try:
        message = {"type": "COMMAND", "id": sensor_id, "command": command}
        sock.sendall(json.dumps(message).encode())
        print(f"Comando enviado: {message}")
    except Exception as e:
        print(f"Erro ao enviar comando: {e}")

# Função principal para interagir com o usuário
def interact_with_gateway(sock):
    try:
        while True:
            print("\n1. Enviar comando ao sensor\n2. Sair")
            option = input("Escolha uma opção: ")

            if option == "1":
                sensor_id = input("ID do sensor: ")
                command = input("Comando (on/off): ")
                send_command(sock, sensor_id, command)

            elif option == "2":
                print("Encerrando cliente...")
                break

            else:
                print("Opção inválida.")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((GATEWAY_IP, GATEWAY_PORT))
    print("Conectado ao gateway.")

    try:
        # Thread para ouvir dados do gateway
        listener_thread = threading.Thread(target=receive_data, args=(sock,))
        listener_thread.daemon = True
        listener_thread.start()

        # Interação com o usuário
        interact_with_gateway(sock)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        sock.close()
        print("Cliente desconectado.")
