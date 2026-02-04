# main.py
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from app.api.v1.endpoints.slides import router as api_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Automatic Course Creation AI")

app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/api/v1/")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")