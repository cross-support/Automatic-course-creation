import json
import re
import time
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Generator, Literal

class SlideLayoutItem(BaseModel):
    type: Literal["표지", "본문", "요약"]
    title: str = Field(description="슬라이드 제목 (입력받은 slide_title 그대로 사용)")
    subtitle: str = Field(description="창작한 소제목")
    text_content: List[str] = Field(description="슬라이드 본문 항목 리스트")
    layout_type: Literal["A", "B", "C", "D", "E"] = Field(description="레이아웃 유형")

class SlideLayoutResponse(BaseModel):
    slides: List[SlideLayoutItem]

class PPTComposerService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key.strip())
        self.SYSTEM_PROMPT = """당신은 e-러닝 강좌의 '슬라이드 구성 및 디자인 전문가'입니다.
        제시된 데이터를 바탕으로 아래의 [설계 원칙]과 [레이아웃 유형]에 맞춰 '슬라이드 기획 JSON'을 작성하세요.

        ### 1. 설계 원칙
        - MODE: STRICT_2P (각 주제당 반드시 2페이지 분할)
        - 서식 금지: 제목 기호(#, ##)와 텍스트 강조 기호(**, __) 절대 사용 금지.
        - 제목 유지: 입력 데이터의 slide_title을 그대로 사용.
        - 소제목 생성 (subtitle): 해당 페이지의 내용을 관통하는 짧고 명확한 소제목 직접 창작.
        - - 지식 확장: '5W1H', '손실 회피', '심리적 안전감', '메모의 기술' 등 비즈니스 프레임워크나 전문 용어가 등장할 경우, 원본 데이터에 내용이 부족하더라도 당신의 지식을 활용하여 '핵심 정의'와 '구체적 설명'을 슬라이드 본문에 반드시 포함시키세요.
        - 분할 로직: 1/2 페이지(Theory/Why), 2/2 페이지(Practice/How) 중심.

        ### 2. 레이아웃 유형
        - A) 도입형 / B) 대조형 / C) 요약형 / D) 프로세스형 / E) 3분할형"""

    def run_composition(self, research_data: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        if not research_data:
            return

        all_slides = []
        first_item = research_data[0]
        
        main_title, unit_subtitle = self._extract_subtitle(first_item['unit_title'])
        cover = {
            "slide_id": "0-1",
            "type": "표지",
            "title": first_item.get('title', '강의명'),
            "subtitle": unit_subtitle,
            "text_content": [f"Unit {first_item['unit_number']}", main_title],
            "layout_type": "A"
        }
        all_slides.append(cover)
        yield {"status": "progress", "message": "🎨 표지 디자인 완료", "data": cover}

        total = len(research_data)
        last_topic_id = 0

        for idx, item in enumerate(research_data):
            topic_id = item['slide_number']
            last_topic_id = topic_id
            
            yield {
                "status": "progress", 
                "message": f"🎨 [{idx+1}/{total}] '{item['slide_title']}' 레이아웃 설계 중...",
                "percent": int((idx / total) * 100)
            }

            try:
                res_data = self._get_design_response(item)
                for page_id, s in enumerate(res_data.get("slides", []), start=1):
                    ordered_s = {"slide_id": f"{topic_id}-{page_id}", **s, "type": "본문"}
                    all_slides.append(ordered_s)
                    yield {"status": "progress", "message": f"✅ Slide {topic_id}-{page_id} 완료", "data": ordered_s}
                time.sleep(0.2)
            except Exception as e:
                yield {"status": "error", "message": f"{topic_id}번 디자인 에러: {str(e)}"}

        try:
            summary = self._get_summary_response(last_topic_id)
            all_slides.append(summary)
            yield {"status": "progress", "message": "📝 최종 요약 슬라이드 완료", "data": summary}
        except: pass

        yield {
            "status": "complete",
            "message": "✨ 모든 디자인 공정 완료!",
            "data": all_slides
        }

    def _extract_subtitle(self, unit_title: str):
        match = re.search(r'(.+?)[\(（](.+?)[\)）]', unit_title)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return unit_title, ""

    def _get_design_response(self, item: Dict):
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"데이터: {json.dumps(item, ensure_ascii=False)}. 슬라이드 2장을 구성해줘."}
            ],
            response_format=SlideLayoutResponse,
        )
        return completion.choices[0].message.parsed.model_dump()

    def _get_summary_response(self, last_id: int):
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": "전체 학습 내용을 요약하는 슬라이드 1장을 구성해줘. layout_type은 C를 사용해."}
            ],
            response_format=SlideLayoutResponse,
        )
        s = completion.choices[0].message.parsed.model_dump()["slides"][0]
        return {"slide_id": f"{last_id + 1}-1", **s, "type": "요약"}