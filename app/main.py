# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import slides 

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(slides.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)