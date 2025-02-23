from fastapi import FastAPI, HTTPException
import socket
import json

app = FastAPI()

# Configuration (replace with your actual values)
GTW_IP = "127.0.0.1"  # Gateway IP
TCP_PORT = 6000       # Gateway TCP port

# Helper function to send a JSON command to the gateway and receive a response
def send_json_command_to_gateway(command):
    try:
        # Create a TCP socket and connect to the gateway
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((GTW_IP, TCP_PORT))

        # Serialize the command to JSON
        json_command = json.dumps(command)

        # Send the JSON command to the gateway
        client_socket.sendall(json_command.encode('utf-8'))

        # Receive the response from the gateway
        response_data = client_socket.recv(1024)
        if not response_data:
            raise HTTPException(status_code=500, detail="No response from gateway")

        # Deserialize the response from JSON
        response = json.loads(response_data.decode('utf-8'))

        # Close the socket
        client_socket.close()

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with gateway: {str(e)}")

# Endpoint to get sensor data
@app.get("/sensor-data")
def get_sensor_data():
    # Create a RECIEVE_DATA command
    command = {
        "type": "RECIEVE_DATA"
    }

    # Send the command to the gateway
    response = send_json_command_to_gateway(command)

    return response

# Endpoint to list connected devices
@app.get("/devices")
def list_devices():
    # Create a LIST command
    command = {
        "type": "LIST"
    }

    # Send the command to the gateway
    response = send_json_command_to_gateway(command)

    return response

# Endpoint to set the state of a device
@app.post("/set-device-state")
def set_device_state(block_id: str, state: bool):
    # Create a SET_STATE command
    command = {
        "type": "SET_STATE",
        "block_id": block_id,
        "state": state
    }

    # Send the command to the gateway
    response = send_json_command_to_gateway(command)

    return response

# Endpoint to check the state of a device
@app.get("/check-device-state")
def check_device_state(block_id: str):
    # Create a CHECK_STATE command
    command = {
        "type": "CHECK_STATE",
        "block_id": block_id
    }

    # Send the command to the gateway
    response = send_json_command_to_gateway(command)

    return response

# Run the FastAPI server with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)