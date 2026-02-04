import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# Services
from app.services.research_service import ResearchService
from app.services.ppt_composer_service import PPTComposerService
from app.services.google_slides_service import GoogleSlidesService
from app.services.slide_workflow_service import SlideWorkflowService

# Dependencies
from app.core.dependencies import (
    get_research_service, 
    get_ppt_composer_service, 
    get_google_slides_service
)

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
    composer_service: PPTComposerService = Depends(get_ppt_composer_service),
    google_service: GoogleSlidesService = Depends(get_google_slides_service)
):
    
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8-sig')
    
    goals_list = [g.strip() for g in learning_goals.split(",") if g.strip()]

    return StreamingResponse(
        SlideWorkflowService.run_generation_pipeline(
            df=df,
            unit_no=unit_no,
            unit_title=unit_title,
            audience=audience,
            goals_list=goals_list,
            research_service=research_service,
            composer_service=composer_service,
            google_service=google_service
        ),
        media_type="application/x-ndjson"
    )