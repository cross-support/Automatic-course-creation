import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Generator

class SlideResponse(BaseModel):
    conclusion: str = Field(description="핵심 요약 1문장.")
    key_messages: List[str] = Field(description="최대 3점. 짧고 간결하게 작성.")
    case_study: str = Field(description="[상황 → 행동 → 결과] 구조의 구체적인 업무 장면.")
    pitfalls: List[str] = Field(description="실무자가 흔히 하는 실수 1~2점.")
    action_item: str = Field(description="강의 직후 즉시 실행할 'Next Step' 1문장.")
    mini_work: str = Field(description="30초 내로 생각 가능한 질문.")
    split_plan: str = Field(description="1/2페이지(Why/What), 2/2페이지(How/Specific) 요소 구분.")
    references: str = Field(description="참고문헌 정보.")

class ResearchService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key.strip())
        self.SYSTEM_INSTRUCTION = """당신은 기업 교육 전문가입니다. 모든 답변은 일본어로 작성하세요.

        ### [필수 작성 원칙]
        1. [형식] 반드시 Markdown 형식을 사용하되, 가독성을 위해 볼드(**) 기호는 절대 사용하지 마십시오.
        2. [내용] 비즈니스와 무관한 추상적 비유(우주, 요리 등)는 금지합니다. 실제 업무 현장 밀착형으로 작성하십시오.
        3. [근거] 출처가 불분명한 통념은 "근거 약함"을 명시하십시오. 공공기관이나 공식 보고서 데이터를 우선적으로 활용하십시오."""

    def run_research(
        self,
        df: pd.DataFrame,
        unit_number: int,
        unit_title: str,
        audience: str,
        learning_goals: List[str]
    ) -> Generator[Dict[str, Any], None, None]:
        
        filtered_df = self._prepare_dataframe(df, unit_number, unit_title)

        if filtered_df.empty:
            yield {"status": "error", "message": "일치하는 유닛을 찾을 수 없습니다."}
            return

        source_data = filtered_df.to_dict(orient="records")
        total = len(source_data)
        all_parsed_data = []

        for idx, item in enumerate(source_data):
            percent = int((idx / total) * 100)
            yield {
                "status": "progress",
                "message": f"[{idx + 1}/{total}] '{item['slide_title']}' 분석 중...",
                "percent": percent
            }

            try:
                res_dict = self._get_ai_response(item['slide_title'], audience, learning_goals)
                final_item = {**item, **res_dict}
                all_parsed_data.append(final_item)
            except Exception as e:
                yield {"status": "error", "message": f"{idx + 1}번 항목 에러: {str(e)}"}

        yield {
            "status": "complete",
            "message": "모든 분석 완료!",
            "percent": 100,
            "data": all_parsed_data
        }

    def _prepare_dataframe(self, df: pd.DataFrame, unit_number: int, unit_title: str) -> pd.DataFrame:
        def normalize(s: Any) -> str:
            return str(s).replace(" ", "").replace("　", "").strip()

        temp_df = df.copy()
        
        temp_df['unit_title_norm'] = temp_df['unit_title'].apply(normalize)
        target_title_norm = normalize(unit_title)
        
        temp_df['unit_number_str'] = (
            pd.to_numeric(temp_df['unit_number'], errors='coerce')
            .fillna(0).astype(int).astype(str)
        )

        return temp_df[
            (temp_df['unit_number_str'] == str(unit_number)) &
            (temp_df['unit_title_norm'] == target_title_norm)
        ].copy()

    def _get_ai_response(self, slide_title: str, audience: str, goals: List[str]) -> Dict[str, Any]:
        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.SYSTEM_INSTRUCTION},
                {"role": "user", "content": f"Title: {slide_title}\nAudience: {audience}\nGoals: {goals}"}
            ],
            response_format=SlideResponse,
        )
        return completion.choices[0].message.parsed.model_dump()