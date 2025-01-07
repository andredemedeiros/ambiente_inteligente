from utils import load_env, set_client_mqtt

env = load_env()

import paho.mqtt.client as paho
from paho import mqtt
import json
import time

power_on = 1
send_time = 0

def on_message(client, userdata, msg):

    global send_time

    if time.time() - send_time >= int(env.TIME_SAMPLE):

        sensor_data = {
            "Tensao": [0, 0, 0],
            "Corrente": [0, 0, 0],
            "Potencia": [0, 0, 0],
        }
        
        if power_on == 1:
            sensor_data = json.loads(str(msg.payload.decode('utf-8')))

        print(sensor_data)
        
        send_time = time.time()



client = paho.Client()
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
client.username_pw_set(env.ACESS_NAME, env.ACESS_PASSWORD)
client.connect(env.URL_BROKER, int(env.PORT_BROKER))
client.on_message = on_message
client.subscribe("ESP32-2")
client.loop_forever()

# client = set_client_mqtt("ESP32-2", env)