import streamlit as st
import socket
import json
import time
import threading
import messages_pb2

RECONNECT_INTERVAL = 10  # Intervalo em segundos para tentar reconectar

# Configurações do Gateway
GATEWAY_IP = "127.0.0.1"
GATEWAY_PORT = 6000

# Função para se conectar ao Gateway
def connect_to_gateway():
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((GATEWAY_IP, GATEWAY_PORT))
        return client_socket
    except Exception as e:
        st.error(f"Erro ao conectar ao Gateway: {e}")
        return None

# Função para listar dispositivos no Gateway
def list_devices(client_socket):
    try:
        client_socket.sendall("LIST_DEVICES".encode("utf-8"))
        response = client_socket.recv(4096).decode("utf-8")
        devices = json.loads(response)
        return devices
    except Exception as e:
        st.error(f"Erro ao listar dispositivos: {e}")
        return []

# Função para solicitar dados sensoriados dos dispositivos
def get_sensor_data(client_socket):
    try:
        client_socket.sendall("RECIEVE_DATA".encode("utf-8"))
        response = client_socket.recv(4096).decode("utf-8")
        return response
    except Exception as e:
        st.error(f"Erro ao obter dados sensoriados: {e}")
        return "Nenhum dado disponível"

# Função para enviar comando para o Gateway
def send_command(client_socket, bloc, command):
    try:
        client_socket.sendall(f"SET_STATE {bloc} {command}".encode("utf-8"))
        st.success(f"Comando enviado: {command} para o bloco {bloc}")
    except Exception as e:
        st.error(f"Erro ao enviar comando: {e}")

# Configuração da interface Streamlit
st.title("Interface de Controle - Ambiente Inteligente")
st.header("Lista de Dispositivos Conectados")

# Conectar ao Gateway
client_socket = connect_to_gateway()
if client_socket:
    # Atualização automática de dados
    placeholder = st.empty()

    # Loop para atualizar dispositivos e dados sensoriados
    while True:
        with placeholder.container():
            # Listar dispositivos
            devices = list_devices(client_socket)
            if devices:
                for device in devices:
                    bloc = device.get("BLOCO", "Desconhecido")
                    tipo = device.get("TIPO", "Desconhecido")
                    estado = device.get("ESTADO", "Desconhecido")

                    st.subheader(f"Dispositivo: {tipo} (Bloco {bloc})")
                    st.text(f"Estado atual: {'Ligado' if estado == '1' else 'Desligado'}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Ligar Bloco {bloc}"):
                            send_command(client_socket, bloc, "1")
                    with col2:
                        if st.button(f"Desligar Bloco {bloc}"):
                            send_command(client_socket, bloc, "0")
            else:
                st.warning("Nenhum dispositivo encontrado no Gateway.")

            # Exibir dados sensoriados
            st.header("Dados Sensoriados")
            sensor_data = get_sensor_data(client_socket)
            st.text(sensor_data)

        # Intervalo de atualização (em segundos)
        time.sleep(5)

    # Fechar conexão com o Gateway
    client_socket.close()
else:
    st.error("Não foi possível conectar ao Gateway.")