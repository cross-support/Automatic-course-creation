import os
import math
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.core.config import settings

COLORS = {
    'NAVY_BG': {'red': 0.15, 'green': 0.17, 'blue': 0.22},
    'ORANGE_POINT': {'red': 0.9, 'green': 0.45, 'blue': 0.1},
    'WHITE': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
    'BG_NORMAL': {'red': 1.0, 'green': 1.0, 'blue': 1.0}, 
    'PRIMARY_NAVY': {'red': 0.0, 'green': 0.0, 'blue': 0.0},
    'GRAY_TEXT': {'red': 0.25, 'green': 0.25, 'blue': 0.25},
    'CHARCOAL_GRAY': {'red': 0.15, 'green': 0.15, 'blue': 0.15},
    'NAVY_POINT': {'red': 0.12, 'green': 0.25, 'blue': 0.53},
    'LIGHT_GRAY': {'red': 0.96, 'green': 0.96, 'blue': 0.96},
    'BLACK': {'red': 0.0, 'green': 0.0, 'blue': 0.0},
    'SOFT_BLACK': {'red': 0.15, 'green': 0.15, 'blue': 0.15},
    'SUB_TITLE': {'red': 0.25, 'green': 0.3, 'blue': 0.4}
}

LAYOUT_CONFIG = {
    'CONTENT_Y_START': 120,
    'SAFE_BOTTOM': 365,
    'BOX_WIDTH': 648,
    'TEXT_WIDTH': 620
}

class GoogleSlidesService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
        self.service = build('slides', 'v1', credentials=self._authenticate())

    def _authenticate(self):
        creds = None
        if os.path.exists(settings.TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(settings.TOKEN_PATH, self.scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(settings.CREDENTIALS_PATH, self.scopes)
                creds = flow.run_local_server(port=0)
            
            with open(settings.TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        return creds

    def create_presentation_from_json(self, slide_data: list):
        if not slide_data or not isinstance(slide_data, list):
            return None, "有効なスライドデータがありません。"

        first_slide = slide_data[0]
        main_title = first_slide.get('title', 'Course') if isinstance(first_slide, dict) else 'Course'
        unit_info = (first_slide.get('text_content', []) or ["Default Unit"])[0]
        file_name = f"{main_title}_{unit_info}"

        presentation = self.service.presentations().create(body={'title': file_name}).execute()
        presentation_id = presentation.get('presentationId')
        
        requests = [{'deleteObject': {'objectId': presentation.get('slides')[0].get('objectId')}}]

        for item in slide_data:
            slide_reqs = self._generate_slide_requests(item)
            requests.extend(slide_reqs)

        self.service.presentations().batchUpdate(presentationId=presentation_id, body={'requests': requests}).execute()
        
        return presentation_id, f"https://docs.google.com/presentation/d/{presentation_id}"

    def _generate_slide_requests(self, item: Dict) -> List[Dict]:
        requests = []
        slide_id = f"id_{item['slide_id'].replace('-', '_').replace('.', '')}"
        
        requests.append({'createSlide': {'objectId': slide_id, 'slideLayoutReference': {'predefinedLayout': 'BLANK'}}})

        if item['type'] in ['表紙']:
            requests.extend(self._create_cover_slide(slide_id, item))
        else:
            requests.extend(self._create_content_slide_base(slide_id, item))
            
            layout_type = item.get('layout_type', 'C')
            content = item.get('text_content', [])
            
            if layout_type == 'A':
                requests.extend(self._layout_A(slide_id, content))
            elif layout_type == 'B':
                requests.extend(self._layout_B(slide_id, content))
            elif layout_type == 'C':
                requests.extend(self._layout_C(slide_id, content))
            elif layout_type == 'D':
                requests.extend(self._layout_D(slide_id, content))
            elif layout_type == 'E':
                requests.extend(self._layout_E(slide_id, content))

            if item.get('supplement'):
                requests.extend(self._create_supplement(slide_id, item['supplement']))

        return requests


    def _create_cover_slide(self, slide_id: str, item: Dict) -> List[Dict]:
            reqs = []
            reqs.append(self._req_update_bg(slide_id, COLORS['NAVY_BG']))
            
            texts = item.get('text_content', [])
            unit_text = texts[0].strip() if len(texts) > 0 else ""
            main_title = texts[1].strip() if len(texts) > 1 else ""
            sub_title = texts[2].strip() if len(texts) > 2 else ""

            title_len = len(main_title)
            font_size = 38
            
            if title_len > 30:
                font_size = 28
            elif title_len > 20:
                font_size = 34
            elif title_len > 15:
                font_size = 38
                
            bar_height = 190

            reqs.extend(self._create_shape_with_style(
                f"bar_{slide_id}", slide_id, 'RECTANGLE', 
                40, 100, 8, bar_height, COLORS['ORANGE_POINT']
            ))
            
            reqs.extend(self._create_text_box(
                f"unit_{slide_id}", slide_id, 
                65, 100, 300, 30, 
                unit_text.upper(), 18, COLORS['ORANGE_POINT'], bold=True
            ))
            
            reqs.extend(self._create_text_box(
                f"main_{slide_id}", slide_id, 
                65, 135, 600, 90, 
                main_title, font_size, COLORS['WHITE'], bold=True
            ))
            
            if sub_title:
                reqs.extend(self._create_text_box(
                    f"sub_{slide_id}", slide_id, 
                    65, 230, 600, 40, 
                    f"～{sub_title}～", 18, COLORS['WHITE']
                ))
            
            return reqs
    
    def _create_content_slide_base(self, slide_id: str, item: Dict) -> List[Dict]:
        reqs = []
        reqs.append(self._req_update_bg(slide_id, COLORS['BG_NORMAL']))
        
        display_title = f"{item['slide_id']}. {item['title']}"
        
        title_len = len(display_title)
        title_font_size = 22 
        
        if title_len > 50:
            title_font_size = 14  
        elif title_len > 40:
            title_font_size = 16  
        elif title_len > 32:
            title_font_size = 18  
        elif title_len > 28:
            title_font_size = 20  
            
        reqs.extend(self._create_text_box(
            f"title_{slide_id}", slide_id, 
            36, 20, 648, 45, 
            display_title, title_font_size, COLORS['PRIMARY_NAVY'], bold=True
        ))
        
        if item.get('subtitle'):
            sub_len = len(item['subtitle'])
            sub_size = 14
            if sub_len > 60: sub_size = 11
            elif sub_len > 50: sub_size = 12
            
            reqs.extend(self._create_text_box(
                f"sub_txt_{slide_id}", slide_id, 
                36, 62, 648, 30, 
                item['subtitle'], sub_size, COLORS['SUB_TITLE'], bold=True
            ))
        
        return reqs

    def _layout_A(self, slide_id: str, content: List[str]) -> List[Dict]:
        reqs = []
        current_y = 105
        
        intro_fsize = 16
        list_fsize = 14
        
        intro_text = content[0] if content else " "
        
        text_w_limit = LAYOUT_CONFIG['TEXT_WIDTH'] - 20 
        estimated_text_h = self._calculate_text_height(intro_text, text_w_limit, intro_fsize)
        
        padding = 30 
        min_height = 60
        box_height = max(min_height, estimated_text_h + padding)
        
        reqs.extend(self._create_shape_with_style(
            f"abg_{slide_id}", slide_id, 'ROUND_RECTANGLE', 
            36, current_y, LAYOUT_CONFIG['BOX_WIDTH'], box_height, COLORS['LIGHT_GRAY']
        ))
        
        reqs.extend(self._create_shape_with_style(
            f"abar_{slide_id}", slide_id, 'RECTANGLE', 
            36, current_y, 6, box_height, COLORS['ORANGE_POINT']
        ))
        
        reqs.extend(self._create_text_box(
            f"atxt_{slide_id}", slide_id, 
            55, current_y, 
            LAYOUT_CONFIG['TEXT_WIDTH'], box_height, 
            intro_text, intro_fsize, COLORS['CHARCOAL_GRAY'], bold=True
        ))
        
        current_y += (box_height + 20)

        for i, txt in enumerate(content[1:]):
            list_h = self._calculate_text_height(f"- {txt}", 600, list_fsize) + 10
            reqs.extend(self._create_text_box(
                f"alist_{i}_{slide_id}", slide_id, 
                45, current_y, 600, list_h, 
                f"- {txt}", list_fsize, COLORS['CHARCOAL_GRAY']
            ))
            current_y += (list_h + 10)
            
        return reqs

    def _layout_B(self, slide_id: str, content: List[str]) -> List[Dict]:
        reqs = []
        current_y = 115
        cnt = len(content)
        
        has_intro = False
        intro_text = ""
        left_items = []
        right_items = []

        if cnt == 2:
            left_items = [content[0]]
            right_items = [content[1]]
        elif cnt == 4:
            left_items = content[:2]  
            right_items = content[2:] 
            
        else:
            half = (cnt + 1) // 2
            left_items = content[:half]
            right_items = content[half:]

        if has_intro:
            intro_h = max(10, self._calculate_text_height(intro_text, LAYOUT_CONFIG['BOX_WIDTH'], 16))
            
            reqs.extend(self._create_text_box(
                f"btxt_intro_{slide_id}", slide_id, 36, current_y, 
                LAYOUT_CONFIG['BOX_WIDTH'], intro_h, intro_text, 16, COLORS['CHARCOAL_GRAY'], bold=True
            ))
            
            current_y += (intro_h + 20)

        card_h = 370 - current_y
        
        cols_data = [
            {"items": left_items, "bg": {'red': 1.0, 'green': 0.94, 'blue': 0.94}, "x": 36},   
            {"items": right_items, "bg": {'red': 0.94, 'green': 1.0, 'blue': 0.94}, "x": 374}  
        ]

        for i, col in enumerate(cols_data):
            processed_items = [item.replace("\n", "\n\n") for item in col['items']]
            
            if len(processed_items) > 1:
                full_text = "\n\n\n".join(processed_items)
            else:
                full_text = processed_items[0] if processed_items else ""

            reqs.extend(self._create_shape_with_style(
                f"bbox_{i}_{slide_id}", slide_id, 'ROUND_RECTANGLE', 
                col['x'], current_y, 310, card_h, col['bg']
            ))
            
            reqs.extend(self._create_text_box(
                f"btxt_{i}_{slide_id}", slide_id, 
                col['x'] + 20, current_y + 20, 270, card_h - 40, 
                full_text, 13, {'red': 0.15, 'green': 0.15, 'blue': 0.15}
            ))

        return reqs
    
    def _layout_C(self, slide_id: str, content: List[str]) -> List[Dict]:
        reqs = []
        current_y = 110
        font_size = 14
        gap = 10

        for i, txt in enumerate(content):
            full_text = f"• {txt}"
            text_h = self._calculate_text_height(full_text, LAYOUT_CONFIG['BOX_WIDTH'], font_size)
            
            reqs.extend(self._create_text_box(f"ctxt_{i}_{slide_id}", slide_id, 36, current_y, LAYOUT_CONFIG['BOX_WIDTH'], text_h, full_text, font_size))
            current_y += (text_h + gap)
            
        return reqs

    def _layout_D(self, slide_id: str, content: List[str]) -> List[Dict]:
            reqs = []
            count = len(content)
            
            start_y = 105
            limit_y = LAYOUT_CONFIG['SAFE_BOTTOM'] 
            available_height = limit_y - start_y
            
            gap = 10 if count >= 4 else 20
            
            total_gap_height = gap * (count - 1)
            box_height = (available_height - total_gap_height) / count
            
            font_size = 12 if count >= 4 else 14
            
            current_y = start_y

            for i, txt in enumerate(content):
                display_txt = txt
                
                reqs.extend(self._create_shape_with_style(
                    f"dbg_{i}_{slide_id}", slide_id, 'ROUND_RECTANGLE', 
                    36, current_y, 648, box_height, COLORS['LIGHT_GRAY']
                ))
                
                reqs.extend(self._create_shape_with_style(
                    f"dbar_{i}_{slide_id}", slide_id, 'RECTANGLE', 
                    36, current_y, 4, box_height, COLORS['ORANGE_POINT']
                ))
                
                reqs.extend(self._create_text_box(
                    f"dtxt_{i}_{slide_id}", slide_id, 
                    55, current_y, 580, box_height, 
                    display_txt, font_size, COLORS['SOFT_BLACK']
                ))
                
                current_y += (box_height + gap)
                
            return reqs

    def _layout_E(self, slide_id: str, content: List[str]) -> List[Dict]:
        reqs = []
        themes = [
            {'bg': {'red': 0.94, 'green': 0.96, 'blue': 1.0}, 'bar': {'red': 0.12, 'green': 0.44, 'blue': 0.93}, 'x': 36},
            {'bg': {'red': 1.0, 'green': 0.94, 'blue': 0.94}, 'bar': {'red': 0.91, 'green': 0.22, 'blue': 0.38}, 'x': 268},
            {'bg': {'red': 1.0, 'green': 0.98, 'blue': 0.92}, 'bar': {'red': 0.82, 'green': 0.52, 'blue': 0.12}, 'x': 500}
        ]
        
        chunk_size = (len(content) + 2) // 3
        columns = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        y_pos = 115

        for i, col_data in enumerate(columns):
            if i > 2: break
            theme = themes[i]
            display_txt = "\n\n".join(col_data)
            
            reqs.extend(self._create_shape_with_style(f"ebg_{i}_{slide_id}", slide_id, 'RECTANGLE', theme['x'], y_pos, 210, 260, theme['bg']))
            reqs.extend(self._create_shape_with_style(f"ebar_{i}_{slide_id}", slide_id, 'RECTANGLE', theme['x'], y_pos, 4, 260, theme['bar']))
            
            txt_reqs = self._create_text_box(f"etxt_{i}_{slide_id}", slide_id, theme['x'] + 15, y_pos, 180, 260, display_txt, 13, COLORS['SOFT_BLACK'])
            txt_reqs[-1]['updateParagraphStyle']['style']['alignment'] = 'CENTER'
            reqs.extend(txt_reqs)
            
        return reqs

    def _create_supplement(self, slide_id: str, text: str) -> List[Dict]:
        return self._create_text_box(f"supp_{slide_id}", slide_id, 36, LAYOUT_CONFIG['SAFE_BOTTOM'] - 30, 648, 30, text, 10, COLORS['GRAY_TEXT'], italic=True)

    def _req_update_bg(self, slide_id: str, color: Dict) -> Dict:
        return {
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': color}}}},
                'fields': 'pageBackgroundFill.solidFill.color'
            }
        }

    def _create_shape_with_style(self, obj_id: str, page_id: str, shape_type: str, x, y, w, h, bg_color: Dict) -> List[Dict]:
        return [
            {
                'createShape': {
                    'objectId': obj_id,
                    'shapeType': shape_type,
                    'elementProperties': {
                        'pageObjectId': page_id,
                        'size': {'width': {'magnitude': w, 'unit': 'PT'}, 'height': {'magnitude': h, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': x, 'translateY': y, 'unit': 'PT'}
                    }
                }
            },
            {
                'updateShapeProperties': {
                    'objectId': obj_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': bg_color}}},
                        'outline': {'propertyState': 'NOT_RENDERED'}
                    },
                    'fields': 'shapeBackgroundFill.solidFill.color,outline'
                }
            }
        ]

    def _create_text_box(self, obj_id: str, page_id: str, x, y, w, h, text: str, 
                         font_size: int, color: Dict = None, bold: bool = False, italic: bool = False) -> List[Dict]:
        requests = [
            {
                'createShape': {
                    'objectId': obj_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': page_id,
                        'size': {'width': {'magnitude': w, 'unit': 'PT'}, 'height': {'magnitude': h, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': x, 'translateY': y, 'unit': 'PT'}
                    }
                }
            },
            {'insertText': {'objectId': obj_id, 'text': text}}
        ]
        
        style = {
            'fontSize': {'magnitude': font_size, 'unit': 'PT'},
            'fontFamily': 'Noto Sans JP',
            'bold': bold,
            'italic': italic
        }
        fields = 'fontSize,fontFamily,bold,italic'
        
        if color:
            style['foregroundColor'] = {'opaqueColor': {'rgbColor': color}}
            fields += ',foregroundColor'

        requests.append({
            'updateTextStyle': {
                'objectId': obj_id,
                'style': style,
                'fields': fields
            }
        })
        
        requests.append({'updateShapeProperties': {'objectId': obj_id, 'shapeProperties': {'contentAlignment': 'MIDDLE'}, 'fields': 'contentAlignment'}})
        requests.append({'updateParagraphStyle': {'objectId': obj_id, 'style': {'lineSpacing': 130}, 'fields': 'lineSpacing'}})
        
        return requests

    def _calculate_text_height(self, text: str, width_pt: float, font_size: int, line_spacing: float = 1.3) -> float:
            if not text:
                return 30
            
            chars_per_line = int(width_pt / (font_size * 1.05))
            if chars_per_line < 1: chars_per_line = 1
            
            lines = text.split('\n')
            total_lines = 0
            
            for line in lines:
                length = len(line)
                if length == 0:
                    total_lines += 1
                else:
                    total_lines += math.ceil(length / chars_per_line)
            
            return (total_lines * font_size * line_spacing)