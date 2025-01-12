import socket
import threading
import time
import messages_pb2
import streamlit as st
import pandas as pd
from datetime import datetime

RECONNECT_INTERVAL = 10  # Intervalo em segundos para tentar reconectar

# Para armazenar os dados temporais dos dispositivos
device_data = {}

# Função para formatar a hora
def format_time(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def receive_data(client_socket):
    """
    Thread dedicada para receber dados do gateway.
    """
    while True:
        try:
            data = client_socket.recv(1024)
            if data:
                # Desserializa os dados usando Protobuf
                sensor_data_collection = messages_pb2.SensorDataCollection()
                sensor_data_collection.ParseFromString(data)

                # Atualiza os dados dos dispositivos
                for sensor in sensor_data_collection.sensor_data:
                    device_data[sensor.Bloco] = {
                        'Bloco': sensor.Bloco,
                        'Tensao': sensor.Tensao,
                        'Corrente': sensor.Corrente,
                        'Potencia': sensor.Potencia,
                        'Energia': sensor.Energia,
                        'FatorPot': sensor.FatorPot,
                        'Estado': sensor.Estado,
                        'last_updated': time.time()
                    }

        except Exception as e:
            print(f"[ERRO] Erro ao receber dados: {e}")
            break

def send_commands(client_socket, block_id, state):
    """
    Envia comandos ao gateway usando Protobuf.
    """
    try:
        command_msg = messages_pb2.Command()

        command_msg.type = messages_pb2.Command.SET_STATE
        command_msg.block_id = block_id
        command_msg.state = state  # Converte para booleano (True ou False)
        client_socket.sendall(command_msg.SerializeToString())

    except Exception as e:
        print(f"[ERRO] Erro ao enviar comando: {e}")
        return

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

def display_device_data():
    """
    Exibe os dados dos dispositivos no Streamlit.
    """
    if device_data:
        # Cria um DataFrame para mostrar os dispositivos
        df = pd.DataFrame(device_data.values())
        df['last_updated'] = df['last_updated'].apply(format_time)
        st.write("### Dados dos Dispositivos")
        st.dataframe(df)
    else:
        st.write("Nenhum dispositivo conectado.")

def change_device_state(client_socket, device_id, new_state):
    """
    Altera o estado de um dispositivo.
    """
    if device_id in device_data:
        send_commands(client_socket, device_id, new_state)
        device_data[device_id]['Estado'] = new_state
        st.success(f"Estado do dispositivo {device_id} alterado para {new_state}.")
    else:
        st.error(f"Dispositivo {device_id} não encontrado.")

def main():
    server_ip = "127.0.0.1"  # Substitua pelo IP do gateway
    server_port = 6000

    st.title('Monitoramento e Controle de Dispositivos')

    # Conecta ao gateway
    client_socket = connect_to_gateway(server_ip, server_port)

    # Cria threads separadas para envio e recepção
    receive_thread = threading.Thread(target=receive_data, args=(client_socket,))
    receive_thread.daemon = True
    receive_thread.start()

    # Exibe os dados dos dispositivos
    display_device_data()

    # Botão para alterar o estado de um dispositivo
    with st.form(key='change_state_form'):
        device_id_input = st.text_input("ID do Dispositivo", "Bloco1")  # ID do Bloco
        new_state_input = st.selectbox("Novo Estado", ["ON", "OFF"])

        submit_button = st.form_submit_button(label="Alterar Estado")

        if submit_button:
            new_state = True if new_state_input == "ON" else False
            change_device_state(client_socket, device_id_input, new_state)

    # Atualiza a interface a cada 5 segundos para refletir os dados mais recentes
    st.experimental_rerun()

if __name__ == "__main__":
    main()
