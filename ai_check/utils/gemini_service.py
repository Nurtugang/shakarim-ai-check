import re
import os
import json
import logging
import datetime

from google import genai
from google.genai import types
from google.genai.types import FinishReason

from shakarim_ai_check.gemini_config import client
from .system_prompt import get_system_prompt
from .analysis_tools import _get_analysis_tools
from .error_utils import fix_truncated_json, process_error_positions

from django.conf import settings

logger = logging.getLogger('ai_check')


def analyze_document(text, additional_instructions="", html_content=None):
    """
    Анализирует текст документа с помощью Gemini API и возвращает структурированный результат
    
    Args:
        text: Текст документа для анализа
        additional_instructions: Дополнительные инструкции для анализа
        html_content: HTML-версия документа для лучшего маппинга позиций
        
    Returns:
        dict: Структурированный результат анализа
    """
    
    system_instruction = get_system_prompt(additional_instructions)
    tools = _get_analysis_tools()
    
    try:
        max_text_length = 1000000
        text_for_analysis = text
        if len(text) > max_text_length:
            text_for_analysis = text[:max_text_length] + "...\n[Текст был сокращен из-за ограничений размера]"
        
        prompt = f"Проанализируй следующий академический документ:\n\n{text_for_analysis}"
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0,
                system_instruction=system_instruction,
                tools=tools
            )
        )
        
        save_gemini_response(response)
        
        # Если ответ был обрезан из-за лимита токенов, пытаемся исправить JSON
        if (response.candidates and response.candidates[0].finish_reason == FinishReason.MAX_TOKENS):
            logger.warning("Gemini response was truncated due to MAX_TOKENS limit, attempting to fix JSON")
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    try:
                        fixed_result = fix_truncated_json(part.text)
                        if fixed_result:
                            if 'errors' in fixed_result:
                                fixed_result['errors'] = process_error_positions(text, fixed_result['errors'], html_content)
                            return fixed_result
                    except Exception as e:
                        logger.error(f"Failed to fix truncated JSON: {str(e)}")
            return {
                "error": "Ответ от Gemini был обрезан из-за лимита токенов. Попробуйте загрузить более короткий документ.",
                "finish_reason": "MAX_TOKENS"
            }
        
        # Если ответ не обрезан и отработал успешно
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    if part.function_call.name == "analyze_document":
                        try:
                            result = json.loads(part.function_call.args)
                            if 'errors' in result:
                                result['errors'] = process_error_positions(text, result['errors'], html_content)
                            return result
                        except Exception as e:
                            logger.error(f"Error parsing function call result: {str(e)}")
                            
                if hasattr(part, 'text') and part.text:
                    result = _parse_json_from_text(part.text)
                    if result:
                        # Обрабатываем ошибки
                        if 'errors' in result:
                            result['errors'] = process_error_positions(text, result['errors'], html_content)
                        return result
                    continue
                        
            # Если ничего не сработало, возвращаем ошибку с подробностями
            return {
                "error": "Не удалось получить структурированный ответ от API",
                "debug_info": {
                    "candidates_count": len(response.candidates) if response.candidates else 0,
                    "parts_count": len(response.candidates[0].content.parts) if response.candidates and response.candidates[0].content.parts else 0,
                    "raw_response": response.text if hasattr(response, 'text') else None
                }
            }
                
        return {
            "error": "Не удалось получить ответ от API Gemini",
            "raw_response": response.text if hasattr(response, 'text') else str(response)
        }
        
    except Exception as e:
        return {
            "error": f"Ошибка при запросе к Gemini API: {str(e)}",
            "raw_response": None
        }


def _parse_json_from_text(raw_text):
    """
    Извлекает и парсит JSON из текстового ответа Gemini
    
    Args:
        raw_text: Сырой текстовый ответ от Gemini
        
    Returns:
        dict: Распарсенный JSON или None если не получилось
    """
    try:
        logger.info(f"Trying to parse text response: {raw_text[:500]}...")
        
        json_str = raw_text.strip()
        if json_str.startswith('```json'):
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif json_str.startswith('```'):
            json_str = json_str.split('```')[1].split('```')[0].strip()
            
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
        json_str = json_str.replace('\t', ' ')

        if json_str.count('"') % 2 != 0:
            last_quote = json_str.rfind('"')
            if last_quote > 0:
                temp_str = json_str[:last_quote]
                last_brace = max(temp_str.rfind('}'), temp_str.rfind(']'))
                if last_brace > 0:
                    json_str = json_str[:last_brace + 1]
                    logger.warning("JSON was truncated due to unterminated string")

        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        logger.error(f"Raw response: {raw_text}")
        return None
    except Exception as e:
        logger.error(f"Error parsing text response: {str(e)}")
        return None
    

def save_gemini_response(response):
    """Сохраняет сырой ответ от Gemini в файл"""
    try:
        tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gemini_{timestamp}.txt"
        filepath = os.path.join(tmp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(response))
        
        logger.info(f"Gemini response saved to: {filename}")
        
    except Exception as e:
        logger.error(f"Failed to save Gemini response: {str(e)}")