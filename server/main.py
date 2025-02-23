import signal
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Cuida no Get"}


@app.get("/device/all")
def read_devices():
    try:
        return{"message": "All devices"}
    except Exception as e:
        print(f"An error occurred: {e}")

@app.get("/device/name/{name}")
def read_name_device():
    
    try:
        return{"message": "Single device name"}
    except Exception as e:
        print(f"An error occurred: {e}")


@app.get("/device/id/{id}")
def read_id_device():
    try:
        return{"message": "Single device id"}
    except Exception as e:
        print(f"An error occurred: {e}")


@app.post("/device/id/{id}")
def set_status():
    try:
        return{"message": "Status set on device {id}"}
    except Exception as e:
        print(f"An exception occurred: {e}")







def handle_shutdown(signal, frame):
    print("Shutting down smoothly...")
    sys.exit(0)

if __name__ == "__main__":

    signal.signal(signal.SIGINT, handle_shutdown)

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload = True)