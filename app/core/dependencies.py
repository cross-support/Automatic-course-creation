from app.core.config import settings
from app.services.research_service import ResearchService
from app.services.ppt_composer_service import PPTComposerService

def get_research_service() -> ResearchService:
    return ResearchService(api_key=settings.OPENAI_API_KEY)

def get_ppt_composer_service() -> PPTComposerService:
    return PPTComposerService(api_key=settings.OPENAI_API_KEY)