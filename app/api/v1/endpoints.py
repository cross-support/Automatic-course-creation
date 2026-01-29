# app/api/v1/endpoints.py
import io
import json
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from app.services.research_service import ResearchService
from app.core.dependencies import get_research_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    # 첫 화면은 index.html
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/research/preview")
async def process_a1_preview(
    unit_no: int = Form(...),
    unit_title: str = Form(...),
    audience: str = Form(...),
    learning_goals: str = Form(...),
    file: UploadFile = File(...),
    service: ResearchService = Depends(get_research_service)
):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8-sig')
    goals_list = [g.strip() for g in learning_goals.split(",") if g.strip()]

    def event_generator():
        for update in service.run_research(df, unit_no, unit_title, audience, goals_list):
            yield json.dumps(update, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")