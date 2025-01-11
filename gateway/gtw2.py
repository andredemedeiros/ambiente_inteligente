import socket
import struct
import threading
import time
import json
import box
from dotenv import dotenv_values

# Configurações
env = box.Box(dotenv_values(".env"))

MCAST_GRP = env.MCAST_GRP
MCAST_PORT = int(env.MCAST_PORT)
GTW_IP = env.GTW_IP
GTW_UDP_PORT = int(env.GTW_UDP_PORT)  # Porta para receber dados UDP de sensores
BUFFER_SIZE = int(env.BUFFER_SIZE)

devices = []  # Lista de dispositivos disponíveis via multicast UDP

GATEWAY_CLIENT_TCP_PORT = 6000  ##teste porta para conexão com cliente







