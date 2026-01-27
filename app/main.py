# main.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Forked Project is Running with FastAPI"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)