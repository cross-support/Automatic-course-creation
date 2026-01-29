import io
import json
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.services.research_service import ResearchService
from app.services.ppt_composer_service import PPTComposerService
from app.core.dependencies import get_research_service, get_ppt_composer_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/research/preview")
async def process_a1_preview(
    unit_no: int = Form(...),
    unit_title: str = Form(...),
    audience: str = Form(...),
    learning_goals: str = Form(...),
    file: UploadFile = File(...),
    research_service: ResearchService = Depends(get_research_service),
    composer_service: PPTComposerService = Depends(get_ppt_composer_service)
):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8-sig')
    goals_list = [g.strip() for g in learning_goals.split(",") if g.strip()]

    def event_generator():
        research_results = []
        
        for update in research_service.run_research(df, unit_no, unit_title, audience, goals_list):
            if update.get("status") == "complete":
                research_results = update.get("data", [])
            
            yield json.dumps(update, ensure_ascii=False) + "\n"
            
        if research_results:
            yield json.dumps({
                "status": "progress", 
                "message": "🎨 원고 분석 완료! 이제 슬라이드 구성을 시작합니다...",
                "percent": 0
            }, ensure_ascii=False) + "\n"
            
            for design_update in composer_service.run_composition(research_results):
                yield json.dumps(design_update, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")