from dotenv import dotenv_values
import box

import paho.mqtt.client as paho
from paho import mqtt


def load_env(env_path: str = ".env") -> dict:
    return box.Box(dotenv_values(env_path))

def on_message(client, userdata, msg: str = ""):
    print(str(msg.payload))

def set_client_mqtt(topic: str = "ESP32-1", env: dict = []) -> paho.Client:

    client = paho.Client()
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client.username_pw_set(env.ACESS_NAME, env.ACESS_PASSWORD)
    client.connect(env.URL_BROKER, int(env.PORT_BROKER))
    client.on_message = on_message
    client.subscribe(topic)
    client.loop_forever()

    return client