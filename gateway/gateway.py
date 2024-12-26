import socket
import struct
import threading
import time
import proto_pb2  # Importando as mensagens do arquivo .proto gerado

# Multicast UDP para descobrir dispositivos
MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007

# Servidor TCP do Gateway
GATEWAY_TCP_PORT = 6000
GATEWAY_HOST = '0.0.0.0'

devices = []  # Lista de dispositivos conectados

def udp_multicast_receiver():
    """Recebe mensagens de descoberta de dispositivos via multicast"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.bind(('', MULTICAST_PORT))
    
    # Inscrever-se no grupo multicast
    group = socket.inet_aton(MULTICAST_GROUP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Mensagem recebida de {addr}")
        # Deserializa a mensagem recebida (PROTOBUF)
        device_info = proto_pb2.DeviceInfo()
        device_info.ParseFromString(data)
        print(f"Dispositivo encontrado: {device_info}")
        devices.append(device_info)

def tcp_server():
    """Servidor TCP do Gateway para comunicação com Cliente"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((GATEWAY_HOST, GATEWAY_TCP_PORT))
    server_socket.listen(5)
    
    print("Gateway esperando por conexões...")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Cliente conectado: {addr}")
        
        # Receber dados e processar comandos
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            
            # Deserializa o comando do Cliente
            command = proto_pb2.DeviceCommand()
            command.ParseFromString(data)
            
            # Executa o comando
            print(f"Comando recebido: {command}")
            for device in devices:
                if device.ip == command.device_id:
                    if command.command == "LIGAR":
                        device.state = True
                    elif command.command == "DESLIGAR":
                        device.state = False
                    # Atualizar estado do dispositivo no cliente
                    status = proto_pb2.DeviceStatus(device_id=device.ip, state=device.state)
                    client_socket.send(status.SerializeToString())

def main():
    """Inicia o Gateway, recepção de multicast e servidor TCP"""
    threading.Thread(target=udp_multicast_receiver, daemon=True).start()
    threading.Thread(target=tcp_server, daemon=True).start()
    
    while True:
        time.sleep(10)  # O Gateway continua ativo

if __name__ == "__main__":
    main()
