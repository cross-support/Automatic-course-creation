import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Generator, Literal, Tuple

from openai import OpenAI, RateLimitError, APITimeoutError
from pydantic import BaseModel, Field

GPT_MODEL = "gpt-4o"

class SlideLayoutItem(BaseModel):
    type: Literal["表紙", "本文", "要約"]
    title: str = Field(description="スライド タイトル(入力された slide_title そのまま使用)")
    subtitle: str = Field(description="該当ページの核心内容を盛り込んであなたが作成した小見出し")
    text_content: List[str] = Field(
        description=(
            "スライドの箇条書きに適した、簡潔でインパクトのある短い文章のリスト。"  
            "冗長な説明は省き、核心のみを要約してください。"
            "(必ず2〜4個の範囲)"
        ),
        min_length=2,
        max_length=4
    )
    layout_type: Literal["A", "B", "C", "D", "E"] = Field(description="レイアウトタイプ")

class SlideLayoutResponse(BaseModel):
    slides: List[SlideLayoutItem]

class PPTComposerService:
    SYSTEM_PROMPT = """あなたはeラーニング講座の「スライド構成およびデザインの専門家」です。
    提示されたデータをもとに、以下の「設計原則」と「レイアウトタイプ」に合わせて「スライド企画JSON」を作成してください。

    ### 1.設計原則
    - MODE:STRICT_2P (各テーマごとに必ず2ページ分割)
    - 書式禁止: タイトル記号（例: #、##、###）とテキスト強調記号（例:**、__)は絶対に使用しないでください。
    - タイトル保持:スライドのタイトル（`title`）は、入力データのタイトル（`slide_title`）を絶対に任意に変更せずにそのまま使用してください。
    - 小見出し生成(subtitle):各スライドの「subtitle」フィールドには、該当ページの内容を貫く短く明確な小見出しをあなたが直接創作して入れてください。
    - 知識拡張:「5W1H」、「損失回避」、「心理的安全感」、「メモの技術」などのビジネスフレームワークや専門用語が登場する場合、原本データに内容が足りなくても、あなたの知識を活用して「核心定義」と「具体的説明」をスライド本文に必ず含めてください。
    - 分割ロジック:
    * 1/2 ページ(Theory):定義(What)、背景/理由(Why)、概念説明中心。
    * 2/2 ページ(Practice):具体的方法(How)、事例(Case)、実践ガイド中心。
    - 禁止事項: 「~を参考にしてください」、「~を確認しましょう」のようにスライド内に情報がない無責任な文句は絶対に使用しないでください。 すべての情報は、スライド本文テキスト内に完結した文章として存在する必要があります。 特に[事例]は状況-行動-結果に要約して直接記載してください。
    - コンテンツ量制御: `text_content` の項目数は必ず「2〜4個」の範囲に収めてください。情報が多い場合は重要度の高い順に4つまで絞り込み、決して4個を超えてはいけません

    ### 2.レイアウトタイプ(A、B、C、D、E)
    データのパターンを分析して、以下のルールに従ってレイアウトを決定してください。
    - A) [導入型]:概念の定義、歴史、背景など「何(What)」や「なぜ(Why)」を初めて説明する時。
    - B) [対照型]: 概念を明確に比較または対照する場合(例:Do & Don't、Before & After、長所 vs 短所）。
    * 適用条件:内容が「2つ」または「4つ」にまとめられる場合に選択。
    - C) [要約型]: 4 つ以上の一般的な項目を一覧表示したり、全体の内容を整理したりするとき。
    * 制約: 項目が5つ以上ある場合は、重要度順に統合・要約して「最大4つ」に収めてください。
    - D) [プロセス型]: 時間の流れ、業務手順、段階別の変化が含まれた内容の場合。
    - E) [3分割型]: 並列的な3大原則や、3つの核心要素を説明するとき。
    * 必須条件: text_contentの項目数が「正確に3個」の場合にのみ選択可能です。2個や4個の場合は絶対に使用しないでください。"""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key.strip())

    def run_composition(self, research_data: List[Dict[str, Any]], max_workers: int = 5) -> Generator[Dict[str, Any], None, None]:
        if not research_data:
            return

        first_item = research_data[0]
        cover = self._create_cover_slide(first_item)
        all_slides = [cover]
        yield {"status": "progress", "message": "表紙デザイン完了", "data": cover}

        total = len(research_data)
        results = [None] * total

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._get_design_response, item): idx 
                for idx, item in enumerate(research_data)
            }

            completed_count = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                item = research_data[idx]
                topic_id = item.get('slide_number', idx + 1)
                
                try:
                    res_data = future.result()
                    slides = []
                    
                    for page_num, s in enumerate(res_data.get("slides", []), start=1):
                        slide_item = {
                            "slide_id": f"{topic_id}-{page_num}", 
                            **s, 
                            "type": "本文"
                        }
                        slides.append(slide_item)
                    
                    results[idx] = slides
                    completed_count += 1
                    
                    yield {
                        "status": "progress", 
                        "message": f"🎨 [{completed_count}/{total}] '{item.get('slide_title', 'タイトルなし')}' 設計完了",
                        "percent": int((completed_count / total) * 100)
                    }

                except Exception as e:
                    yield {"status": "error", "message": f"{topic_id}項目 デザインエラー: {str(e)}"}

        for slides in results:
            if slides:
                all_slides.extend(slides)
                for s in slides:
                     yield {"status": "data", "data": s}

        try:
            last_topic_id = research_data[-1].get('slide_number', total)
            summary = self._get_summary_response(last_topic_id)
            all_slides.append(summary)
            yield {"status": "progress", "message": "📝最終要約スライド 完了", "data": summary}
        except Exception as e:
             yield {"status": "error", "message": f"要約スライドの作成に失敗: {str(e)}"}


        yield {
            "status": "complete",
            "message": "✨すべてのデザイン工程が完了！",
            "data": all_slides
        }

    def _create_cover_slide(self, first_item: Dict[str, Any]) -> Dict[str, Any]:
        raw_unit_title = first_item.get('unit_title', '')
        main_title, sub_title = self._extract_subtitle(raw_unit_title)
        return {
            "slide_id": "0-0",
            "type": "表紙",
            "title": "Cover",
            "layout_type": "Cover",
            "text_content": [f"Unit {first_item.get('unit_number', '1')}", main_title, sub_title]
        }

    def _extract_subtitle(self, text: str) -> Tuple[str, str]:
        if not text:
            return "タイトルなし", ""
            
        match = re.search(r'(.+?)[（\(](.+?)[）\)]', text)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return text.strip(), ""

    def _get_design_response(self, item: Dict) -> Dict[str, Any]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                completion = self.client.beta.chat.completions.parse(
                    model=GPT_MODEL,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": f"データ: {json.dumps(item, ensure_ascii=False)}. スライドを2枚構成して"}
                    ],
                    response_format=SlideLayoutResponse,
                )
                parsed = completion.choices[0].message.parsed
                return parsed.model_dump() if parsed else {"slides": []}
            
            except (RateLimitError, APITimeoutError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"API Rate Limit exceeded after retries: {e}")
            except Exception as e:
                raise RuntimeError(f"API 呼び出し失敗: {e}")

    def _get_summary_response(self, last_id: int) -> Dict[str, Any]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                completion = self.client.beta.chat.completions.parse(
                    model=GPT_MODEL,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": "全体の学習内容を要約するスライドを1枚作成して。 layout_typeはCを使って"}
                    ],
                    response_format=SlideLayoutResponse,
                )
                parsed = completion.choices[0].message.parsed
                if parsed and parsed.slides:
                     s = parsed.slides[0].model_dump()
                     return {"slide_id": f"{last_id + 1}-1", **s, "type": "要約"}
                raise ValueError("要約スライド 作成 結果なし")

            except (RateLimitError, APITimeoutError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise e