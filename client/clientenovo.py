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
def send_command(sock, command):
    try:
        sock.sendall(json.dumps(command).encode())
        print(f"Comando enviado: {command}")
    except Exception as e:
        print(f"Erro ao enviar comando: {e}")

# Função principal para interagir com o usuário
def interact_with_gateway(sock):
    try:
        while True:
            print("\n1. Mostrar atuadores conectados")
            print("2. Enviar comando para atuador")
            print("3. Sair")
            option = input("Escolha uma opção: ")

            if option == "1":
                print("Solicitando lista de atuadores conectados...")
                send_command(sock, {"ACTION": "LIST_DEVICES"})

            elif option == "2":
                bloc_id = input("ID do atuador: ")
                state = input("Comando (on/off): ")
                if state.lower() not in ["on", "off"]:
                    print("Comando inválido. Use 'on' ou 'off'.")
                    continue
                send_command(sock, {"ACTION": "CHANGE_STATE", "BLOCO": bloc_id, "STATE": "1" if state.lower() == "on" else "0"})

            elif option == "3":
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
