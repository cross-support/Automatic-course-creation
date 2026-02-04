import pandas as pd
import time
from openai import OpenAI, RateLimitError, APITimeoutError
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed


GPT_MODEL = "gpt-4o-mini"
    
class SlideResponse(BaseModel):
    conclusion: str = Field(description="核心要約1文")
    key_messages: List[str] = Field(description="最大3点。短く簡潔に")
    case_study: str = Field(description="【状況→行動→結果】 構造の具体的な業務シーン")
    pitfalls: List[str] = Field(description="実務者がよくするミス1~2点")
    action_item: str = Field(description="講義直後にすぐ実行する「Next Step」の1文")
    mini_work: str = Field(description="30秒以内に考えられる質問")
    split_plan: str = Field(description="1/2 ページ(Why/What)、2/2 ページ(How/Specific) 要素区分")
    references: str = Field(description="[タイトル / 著者·機関 / 年 / 要約]")

class ResearchService:
    SYSTEM_INSTRUCTION = """あなたは企業向けeラーニング講座の専門原稿設計者です。 
    下記の「作成原則」を遵守し、挨拶のない本論【No】からスタートのみ出力してください。

    ### [必須作成原則]
    1. [形式] 必ずMarkdown形式を使用するが、可読性のためにボールド(**)記号は絶対に使用しない。
    2. 【内容】ビジネスとは無関係な抽象的比喩（宇宙、料理など）の禁止。 実際の業務現場密着型で作成。
    3. 【根拠】出典不明の通念は"根拠弱"明示。 公共機関/報告書のデータを優先的に活用。"""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key.strip())

    def run_research(
        self,
        df: pd.DataFrame,
        unit_number: int,
        unit_title: str,
        audience: str,
        learning_goals: List[str],
        max_workers: int = 5
    ) -> Generator[Dict[str, Any], None, None]:
        
        filtered_df = self._filter_dataframe(df, unit_number, unit_title)

        if filtered_df.empty:
            yield {"status": "error", "message": "一致するユニットが見つかりません。"}
            return

        source_data = filtered_df.to_dict(orient="records")
        total_count = len(source_data)
        
        results = [None] * total_count

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self._fetch_ai_response, item['slide_title'], audience, learning_goals): idx
                for idx, item in enumerate(source_data)
            }

            completed_count = 0
            
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                completed_count += 1
                percent = int((completed_count / total_count) * 100)
                
                original_item = source_data[idx]

                try:
                    ai_response = future.result()
                    results[idx] = {**original_item, **ai_response}
                    
                    yield {
                        "status": "progress",
                        "message": f"[{completed_count}/{total_count}] {original_item.get('slide_title', 'タイトルなし')}",
                        "percent": percent
                    }
                except Exception as e:
                    results[idx] = original_item 
                    yield {
                        "status": "error", 
                        "message": f"スライド. '{original_item.get('slide_title')}' 処理失敗: {str(e)}"
                    }
                    
        final_results = [r for r in results if r is not None]

        yield {
            "status": "complete",
            "message": "すべての分析が完了！",
            "percent": 100,
            "data": final_results
        }

    def _filter_dataframe(self, df: pd.DataFrame, unit_number: int, unit_title: str) -> pd.DataFrame:
        target_title_norm = str(unit_title).replace(" ", "").replace("　", "").strip()
        
        numeric_col = pd.to_numeric(df['unit_number'], errors='coerce').fillna(0).astype(int)
        mask_number = numeric_col == int(unit_number)

        norm_col = df['unit_title'].astype(str).str.replace(r"\s+", "", regex=True)
        mask_title = norm_col == target_title_norm

        return df[mask_number & mask_title].copy()

    def _fetch_ai_response(self, slide_title: str, audience: str, goals: List[str]) -> Dict[str, Any]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                completion = self.client.beta.chat.completions.parse(
                    model=GPT_MODEL,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_INSTRUCTION},
                        {"role": "user", "content": f"Title: {slide_title}\nAudience: {audience}\nGoals: {', '.join(goals)}"}
                    ],
                    response_format=SlideResponse,
                )
                parsed_data = completion.choices[0].message.parsed
                return parsed_data.model_dump() if parsed_data else {}
            
            except (RateLimitError, APITimeoutError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"API Rate Limit exceeded after retries: {e}")
            except Exception as e:
                raise RuntimeError(f"API Error: {e}")