# Ambiente inteligente

Este é um sistema distribuído que simula um ambiente inteligente, com um Gateway central, dispositivos inteligentes e um Cliente. Ele implementa comunicação entre processos usando sockets TCP e UDP, serialização com Protocol Buffers e descoberta de dispositivos via multicast UDP.

## Estrutura do Repositório

### **gateway/**
O diretório do Gateway contém o código central de controle e monitoramento dos dispositivos.

- **`gateway.py`**: Contém o código principal do Gateway, responsável por gerenciar a comunicação com os dispositivos e o Cliente. Ele se comunica com os dispositivos utilizando TCP e realiza a descoberta via UDP multicast.
- **`proto_pb2.py`**: Arquivo gerado automaticamente pelo `protoc` a partir do arquivo `.proto`, contendo as definições das mensagens Protocol Buffers utilizadas no Gateway.
- **`requirements.txt`**: Lista as dependências necessárias para o Gateway (como `protobuf`, `socket`).

### **devices/**
O diretório dos dispositivos contém o código de simulação de dispositivos inteligentes no ambiente.

- **`lamp_device.py`**: Simula um dispositivo de tipo "Lâmpada". Este é um exemplo de atuador, que pode ser ligado ou desligado e tem controle de intensidade de luz.
- **`ac_device.py`**: Simula um dispositivo do tipo "Ar-Condicionado". Este dispositivo pode ser controlado pelo Gateway.
- **`sensor_device.py`**: Simula um dispositivo sensor (ex: Sensor de temperatura), que envia dados periodicamente (por exemplo, a cada 15 segundos) ao Gateway.
- **`proto_pb2.py`**: Arquivo gerado automaticamente pelo `protoc` para definir as mensagens Protocol Buffers específicas dos dispositivos.
- **`requirements.txt`**: Lista as dependências necessárias para os dispositivos (como `protobuf`, `socket`).

### **client/**
O diretório do Cliente contém o código principal para interação com o Gateway.

- **`client.py`**: Contém o código do Cliente, que se conecta ao Gateway via TCP para consultar os estados dos dispositivos e enviar comandos para controlá-los.
- **`requirements.txt`**: Lista as dependências necessárias para o Cliente (como `protobuf`).

### **proto/**
Contém o arquivo de definições do Protocol Buffers.

- **`smart_home.proto`**: Define as mensagens utilizadas pelo Gateway e pelos dispositivos. Este arquivo contém as definições das mensagens como `DeviceInfo`, `DeviceCommand`, `DeviceStatus`, etc. O arquivo `.proto` é utilizado para gerar os arquivos Python necessários para a comunicação entre os componentes.

---

## Passos para Configuração

### 1. Gerar os Arquivos Python a partir do Arquivo `.proto`
Após criar o arquivo `smart_home.proto`, você precisa gerar os arquivos Python de Protocol Buffers. Use o comando `protoc` para isso. Suponha que o arquivo `smart_home.proto` esteja localizado no diretório `proto/`:

```bash
# Gerar os arquivos Python a partir do arquivo .proto
protoc --python_out=./gateway --python_out=./devices --python_out=./client proto/smart_home.proto

```

### 2. Instalação das dependências

```bash
pip install -r requirements.txt
```

### 3. Execução do cliente

```bash
python3 client/client.py
```

Execução:

1: executar o gateway:
gateway/gtw.py

2: executar os dispositivos:
devices/bloco706.py
devices/bloco727.py

3: executar o cliente:
