import socket
import struct
import json
import time


# Configuração do Multicast
MCAST_GRP   = "228.0.0.8"
MCAST_PORT  = 6789
BROKER_IP   = "606600c5e43b4342b7b5f13ca84351cb.s2.eu.hivemq.cloud"
BROKER_PORT = 8883


def announce_broker():
   """
   Anuncia o IP e a porta do Broker via Multicast para que os dispositivos descubram automaticamente.
   """
   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   ttl = struct.pack('b', 1)
   sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)


   # Monta a mensagem a ser enviada; observe que BROKER_PORT é um número (não uma string)
   broker_msg = {
       "TIPO": "BROKER",
       "IP": BROKER_IP,
       "PORT": BROKER_PORT
   }


   while True:
       try:
           message = json.dumps(broker_msg)
           # Imprime o conteúdo da mensagem para debug
           print(f"[DEBUG] Mensagem JSON enviada: {message}")
           sock.sendto(message.encode('utf-8'), (MCAST_GRP, MCAST_PORT))
           print(f"[INFO] Anunciando Broker: {BROKER_IP}:{BROKER_PORT}")
           time.sleep(5)  # Envia a cada 5 segundos
       except Exception as e:
           print(f"[ERRO] Falha ao anunciar o Broker: {e}")
           break


   sock.close()


if __name__ == "__main__":
   announce_broker()