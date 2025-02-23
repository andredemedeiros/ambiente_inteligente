import socket
import struct
import json
import time
import paho.mqtt.client as mqtt


# Configuração multicast
MCAST_GRP = "228.0.0.8"
MCAST_PORT = 6789
BUFFER_SIZE = 1024


# Configuração padrão do Broker MQTT (caso não seja descoberto via Multicast)
DEFAULT_BROKER_IP = "606600c5e43b4342b7b5f13ca84351cb.s2.eu.hivemq.cloud"
DEFAULT_BROKER_PORT = 8883
ACESS_NAME = "Dispositivo"
ACESS_PASSWORD = "INOVANDo2023"


BROKER_IP = DEFAULT_BROKER_IP
BROKER_PORT = DEFAULT_BROKER_PORT


def discover_broker():
   """
   Descobre o IP do Broker via Multicast UDP.
   """
   global BROKER_IP, BROKER_PORT
   udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
   udp_socket.bind(('', MCAST_PORT))


   mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
   udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


   print("[INFO] Aguardando descoberta do Broker via Multicast...")


   while True:
       try:
           data, addr = udp_socket.recvfrom(BUFFER_SIZE)
           raw_msg = data.decode('utf-8')
           print(f"[DEBUG] Mensagem recebida: {raw_msg}")
           broker_info = json.loads(raw_msg)


           if broker_info.get("TIPO") == "BROKER":
               BROKER_IP = broker_info.get("IP", DEFAULT_BROKER_IP)
               # Converte para inteiro, caso necessário
               try:
                   BROKER_PORT = int(broker_info.get("PORT", DEFAULT_BROKER_PORT))
               except ValueError:
                   print(f"[ERRO] Valor inválido para PORT: {broker_info.get('PORT')}. Usando porta padrão.")
                   BROKER_PORT = DEFAULT_BROKER_PORT


               print(f"[INFO] Broker descoberto: IP={BROKER_IP}, Porta={BROKER_PORT}")
               return BROKER_IP, BROKER_PORT
       except Exception as e:
           print(f"[ERRO] Falha na descoberta do Broker: {e}")
           time.sleep(2)


def connect_mqtt():
   """
   Conecta ao Broker MQTT usando os dados descobertos via Multicast.
   """
   client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
   client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
   client.username_pw_set(ACESS_NAME, ACESS_PASSWORD)


   try:
       client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
       print(f"[INFO] Conectado ao Broker MQTT: {BROKER_IP}:{BROKER_PORT}")
   except Exception as e:
       print(f"[ERRO] Falha ao conectar ao Broker MQTT: {e}")


   return client


def on_message(client, userdata, msg):
   """
   Callback para mensagens recebidas do MQTT.
   """
   print(f"[INFO] Mensagem recebida: {msg.topic} -> {msg.payload.decode('utf-8')}")


def main():
   """
   Descobre o Broker e inicia a conexão MQTT.
   """
   discover_broker()


   client = connect_mqtt()
   client.on_message = on_message
   client.subscribe("sensors/data")
   client.loop_forever()


if __name__ == "__main__":
   main()
