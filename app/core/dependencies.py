from app.core.config import settings
from app.services.research_service import ResearchService

def get_research_service() -> ResearchService:
    return ResearchService(api_key=settings.OPENAI_API_KEY)
