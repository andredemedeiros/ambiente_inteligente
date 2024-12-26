import socket
import time
import proto_pb2  # Importando as mensagens do arquivo .proto gerado

MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007
DISPOSITIVO_PORT = 6001  # Porta TCP do dispositivo

device_info = proto_pb2.DeviceInfo(type="Lâmpada", ip="192.168.0.101", port=DISPOSITIVO_PORT, state=False)

def udp_multicast_sender():
    """Envia a mensagem de descoberta do dispositivo"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        # Serializa a mensagem
        message = device_info.SerializeToString()
        sock.sendto(message, (MULTICAST_GROUP, MULTICAST_PORT))
        print("Dispositivo enviado para o Gateway")
        time.sleep(5)  # Envia a cada 5 segundos

def tcp_client():
    """Cliente TCP que espera comandos do Gateway"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('192.168.0.100', 6000))  # IP do Gateway
    
    while True:
        data = sock.recv(1024)
        if not data:
            break
        
        # Processa os comandos
        command = proto_pb2.DeviceCommand()
        command.ParseFromString(data)
        
        if command.device_id == device_info.ip:
            if command.command == "LIGAR":
                device_info.state = True
            elif command.command == "DESLIGAR":
                device_info.state = False
            
            # Enviar estado de volta
            status = proto_pb2.DeviceStatus(device_id=device_info.ip, state=device_info.state)
            sock.send(status.SerializeToString())

def main():
    """Inicia o dispositivo inteligente"""
    threading.Thread(target=udp_multicast_sender, daemon=True).start()
    threading.Thread(target=tcp_client, daemon=True).start()
    
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
