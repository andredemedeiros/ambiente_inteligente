import streamlit as st
import socket
import proto_pb2  # Arquivo gerado a partir do smart_home.proto
import sys
import time

# Função para conectar ao Gateway via TCP
def connect_to_gateway(gateway_ip, gateway_port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((gateway_ip, gateway_port))
        return client_socket
    except Exception as e:
        st.error(f"Erro ao conectar ao Gateway: {e}")
        return None

# Função para consultar dispositivos conectados
def get_devices(client_socket):
    try:
        # Enviar solicitação para listar dispositivos
        message = proto_pb2.DeviceCommand()
        message.command = "LIST_DEVICES"
        client_socket.sendall(message.SerializeToString())

        # Receber resposta do Gateway
        response = client_socket.recv(1024)
        devices_info = proto_pb2.DeviceInfo()
        devices_info.ParseFromString(response)
        
        return devices_info.devices
    except Exception as e:
        st.error(f"Erro ao obter dispositivos: {e}")
        return []

# Função para enviar comando para dispositivo
def send_device_command(client_socket, device_id, command):
    try:
        message = proto_pb2.DeviceCommand()
        message.device_id = device_id
        message.command = command
        client_socket.sendall(message.SerializeToString())
        st.success(f"Comando '{command}' enviado para o dispositivo {device_id}.")
    except Exception as e:
        st.error(f"Erro ao enviar comando: {e}")

# Configurações da interface Streamlit
st.title("Smart Home Client")
gateway_ip = st.text_input("IP do Gateway", "127.0.0.1")
gateway_port = st.number_input("Porta do Gateway", 5000, 65535, 5000)

# Conectar ao Gateway
client_socket = None
if st.button("Conectar ao Gateway"):
    client_socket = connect_to_gateway(gateway_ip, gateway_port)
    if client_socket:
        st.success("Conectado ao Gateway!")

# Listar dispositivos conectados
if client_socket:
    devices = get_devices(client_socket)
    if devices:
        st.subheader("Dispositivos Conectados")
        device_names = [f"{device.device_id} - {device.device_type}" for device in devices]
        selected_device = st.selectbox("Escolha um dispositivo para controlar", device_names)
        
        # Enviar comando para dispositivo
        device_id = selected_device.split(" - ")[0]  # Extrai o ID do dispositivo
        command = st.selectbox("Escolha um comando", ["Ligar", "Desligar", "Ajustar Temperatura", "Ajustar Intensidade"])
        
        if st.button(f"Enviar comando para {device_id}"):
            if command == "Ligar":
                send_device_command(client_socket, device_id, "TURN_ON")
            elif command == "Desligar":
                send_device_command(client_socket, device_id, "TURN_OFF")
            elif command == "Ajustar Temperatura":
                temp = st.slider("Escolha a temperatura", 16, 30, 22)
                send_device_command(client_socket, device_id, f"SET_TEMPERATURE_{temp}")
            elif command == "Ajustar Intensidade":
                intensity = st.slider("Escolha a intensidade", 0, 100, 50)
                send_device_command(client_socket, device_id, f"SET_INTENSITY_{intensity}")
    else:
        st.warning("Nenhum dispositivo encontrado.")
else:
    st.warning("Conecte-se ao Gateway primeiro.")
