import json
import logging
import copy
from typing import List, Dict, Any, Optional
import pandas as pd

from app.services.research_service import ResearchService
from app.services.ppt_composer_service import PPTComposerService
from app.services.google_slides_service import GoogleSlidesService

logger = logging.getLogger(__name__)

class SlideWorkflowService:
    
    @staticmethod
    def _safe_serialize(data: Any) -> Any:
        try:
            return json.loads(json.dumps(data, ensure_ascii=False))
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON Serialize Warning: {e}. Fallback to raw data.")
            return data

    @staticmethod
    async def run_generation_pipeline(
        df: pd.DataFrame,
        unit_no: int,
        unit_title: str,
        audience: str,
        goals_list: List[str],
        research_service: ResearchService,
        composer_service: PPTComposerService,
        google_service: GoogleSlidesService
    ):
        try:
            research_results = []
            
            for update in research_service.run_research(df, unit_no, unit_title, audience, goals_list):
                if update.get("status") == "complete":
                    research_results = update.get("data", [])
                yield json.dumps(update, ensure_ascii=False) + "\n"

            if not research_results:
                yield json.dumps({"status": "error", "message": "Research 단계에서 데이터가 생성되지 않았습니다."}, ensure_ascii=False) + "\n"
                return

            yield json.dumps({
                "status": "progress", 
                "message": "🎨 スライド配置を設計中です···", 
                "percent": 50 
            }, ensure_ascii=False) + "\n"

            final_composition = []
            temp_collected = []

            for design_update in composer_service.run_composition(research_results):
                if design_update.get("status") == "progress" and "data" in design_update:
                    temp_collected.append(design_update["data"])
                
                if design_update.get("status") == "complete":
                    raw_data = design_update.get("data", temp_collected)
                    final_composition = SlideWorkflowService._safe_serialize(raw_data)

                yield json.dumps(design_update, ensure_ascii=False) + "\n"

            if not final_composition:
                logger.warning("Composition complete signal missing or empty. Using collected temp data.")
                final_composition = temp_collected

            if not final_composition:
                yield json.dumps({"status": "error", "message": "슬라이드 설계 데이터가 비어있습니다."}, ensure_ascii=False) + "\n"
                return

            logger.info(f"Final composition count: {len(final_composition)}")

            yield json.dumps({
                "status": "progress", 
                "message": f"🚀 テストで検証されたロジックで {len(final_composition)}枚のスライドを作成します。", 
                "percent": 90
            }, ensure_ascii=False) + "\n"
            
            pres_id, pres_url = google_service.create_presentation_from_json(final_composition)
            
            yield json.dumps({
                "status": "complete",
                "message": "Googleスライドの作成が完了!",
                "url": pres_url,
                "presentation_id": pres_id,
                "data": final_composition 
            }, ensure_ascii=False) + "\n"

        except Exception as e:
            logger.error(f"Pipeline Critical Error: {str(e)}", exc_info=True)
            yield json.dumps({
                "status": "error", 
                "message": f"시스템 처리 중 오류가 발생했습니다: {str(e)}"
            }, ensure_ascii=False) + "\n"