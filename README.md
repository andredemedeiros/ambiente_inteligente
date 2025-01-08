# Ambiente inteligente

Este é um sistema distribuído que simula um ambiente inteligente, com um Gateway central, dispositivos inteligentes e um Cliente. Ele implementa comunicação entre processos usando sockets TCP e UDP, serialização com Protocol Buffers e descoberta de dispositivos via multicast UDP.

## Estrutura do Repositório

### **gateway/**
O diretório do Gateway contém o código central de controle e monitoramento dos dispositivos.

### **devices/**
O diretório dos dispositivos contém o código de simulação de dispositivos inteligentes no ambiente.

- **`bloco706.py`**: Possui um sensor de energia e um simulador de atuador de energia no bloco 706.
- **`bloco727.py`**: Possui um sensor de energia e um simulador de atuador de energia no bloco 727.

### **client/**
O diretório do Cliente contém o código principal para interação do cliente com o Gateway.

- **`client.py`**: Contém o código do Cliente, que se conecta diretamente ao Gateway via TCP e UDP. O cliente recebe os dados dos sensores via UDP e altera o estados dos dispositivos via TCP.
- **`site.py`**: Código para gerar uma interface de visualização de dados com a biblioteca streamilit.

- **`data/`**: Diretório para armazenas os dados recebidos pelo cliente no fomarto de arquivos csv.

### **proto/**
Contém o arquivo de definições do Protocol Buffers.

- **`msgs.proto`**: Define as mensagens utilizadas pelo Gateway e pelos dispositivos. Este arquivo contém as definições das mensagens. O arquivo `.proto` é utilizado para gerar os arquivos Python necessários para a comunicação entre os componentes.

---

## Execução

### 1. Executar processos devices

```bash
devices/bloco706.py
devices/bloco727.py
```

### 2. Executar processo gateway

```bash
gateway/gtw.py
```

### 3. Executar processo do cliente

```bash
client/client.py
```

### 4. Executar processo da interface

```bash
client/site.py
```