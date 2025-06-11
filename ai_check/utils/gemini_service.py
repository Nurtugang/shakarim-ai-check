from google import genai
from google.genai import types
import json
from shakarim_ai_check.gemini_config import client
from .system_prompt import get_system_prompt

def analyze_document(text, additional_instructions=""):
    """
    Анализирует текст документа с помощью Gemini API и возвращает структурированный результат
    
    Args:
        text: Текст документа для анализа
        additional_instructions: Дополнительные инструкции для анализа
        
    Returns:
        dict: Структурированный результат анализа
    """
    # Получаем системную инструкцию
    system_instruction = get_system_prompt(additional_instructions)
    
    # Структура вывода для функции
    tools = [{
        "function_declarations": [{
            "name": "analyze_document",
            "description": "Анализирует академический документ и возвращает структурированную оценку",
            "parameters": {
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number", "description": "Оценка структуры документа от 0 до 100"},
                            "analysis": {"type": "string", "description": "Подробный анализ структуры документа"},
                            "strengths": {"type": "array", "items": {"type": "string"}, "description": "Сильные стороны структуры"},
                            "weaknesses": {"type": "array", "items": {"type": "string"}, "description": "Слабые стороны структуры"}
                        },
                        "required": ["score", "analysis", "strengths", "weaknesses"]
                    },
                    "logic": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number", "description": "Оценка логики изложения от 0 до 100"},
                            "analysis": {"type": "string", "description": "Подробный анализ логики изложения"},
                            "strengths": {"type": "array", "items": {"type": "string"}, "description": "Сильные стороны логики"},
                            "weaknesses": {"type": "array", "items": {"type": "string"}, "description": "Слабые стороны логики"}
                        },
                        "required": ["score", "analysis", "strengths", "weaknesses"]
                    },
                    "grammar": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number", "description": "Оценка грамматики и стиля от 0 до 100"},
                            "analysis": {"type": "string", "description": "Подробный анализ грамматики и стиля"},
                            "strengths": {"type": "array", "items": {"type": "string"}, "description": "Сильные стороны грамматики"},
                            "weaknesses": {"type": "array", "items": {"type": "string"}, "description": "Слабые стороны грамматики"}
                        },
                        "required": ["score", "analysis", "strengths", "weaknesses"]
                    },
                    "originality": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number", "description": "Оценка оригинальности от 0 до 100"},
                            "analysis": {"type": "string", "description": "Подробный анализ оригинальности"},
                            "strengths": {"type": "array", "items": {"type": "string"}, "description": "Сильные стороны оригинальности"},
                            "weaknesses": {"type": "array", "items": {"type": "string"}, "description": "Слабые стороны оригинальности"}
                        },
                        "required": ["score", "analysis", "strengths", "weaknesses"]
                    },
                    "recommendations": {
                        "type": "object",
                        "properties": {
                            "general": {"type": "array", "items": {"type": "string"}, "description": "Общие рекомендации"},
                            "structure": {"type": "array", "items": {"type": "string"}, "description": "Рекомендации по структуре"},
                            "logic": {"type": "array", "items": {"type": "string"}, "description": "Рекомендации по логике"},
                            "grammar": {"type": "array", "items": {"type": "string"}, "description": "Рекомендации по грамматике"},
                            "originality": {"type": "array", "items": {"type": "string"}, "description": "Рекомендации по оригинальности"}
                        },
                        "required": ["general", "structure", "logic", "grammar", "originality"]
                    },
                    "errors": {
                        "type": "array",
                        "description": "Массив найденных ошибок и проблем",
                        "items": {
                            "type": "object",
                            "properties": {
                                "quote": {"type": "string", "description": "Точная цитата из текста с ошибкой"},
                                "error_type": {"type": "string", "enum": ["grammar", "style", "logic", "structure"], "description": "Тип ошибки"},
                                "description": {"type": "string", "description": "Описание проблемы"},
                                "suggestion": {"type": "string", "description": "Предложение по исправлению"},
                                "severity": {"type": "string", "enum": ["high", "medium", "low"], "description": "Критичность ошибки"}
                            },
                            "required": ["quote", "error_type", "description", "suggestion", "severity"]
                        }
                    }
                },
                "required": ["structure", "logic", "grammar", "originality", "recommendations", "errors"]
            }
        }]
    }]

    try:
        # Ограничиваем размер текста, если он слишком большой
        max_text_length = 120000  # обновленный лимит
        text_for_analysis = text
        if len(text) > max_text_length:
            text_for_analysis = text[:max_text_length] + "...\n[Текст был сокращен из-за ограничений размера]"
        
        # Формируем запрос к API
        prompt = f"Проанализируй следующий академический документ:\n\n{text_for_analysis}"
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                max_output_tokens=8192,  # увеличен для массива ошибок
                temperature=0,
                system_instruction=system_instruction,
                tools=tools
            )
        )
        
        # Если используется функциональный вызов, получаем данные из него
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    if part.function_call.name == "analyze_document":
                        # Преобразуем результат в словарь Python
                        result = json.loads(part.function_call.args)
                        
                        # Обрабатываем ошибки - добавляем позиции в тексте
                        if 'errors' in result:
                            result['errors'] = process_error_positions(text_for_analysis, result['errors'])
                        
                        return result
            
            # Если функциональный вызов не сработал, пытаемся распарсить текст
            raw_response = response.text
            try:
                # Попытка извлечь JSON из текста
                json_str = raw_response.strip()
                if json_str.startswith('```json'):
                    json_str = json_str.split('```json')[1].split('```')[0].strip()
                elif json_str.startswith('```'):
                    json_str = json_str.split('```')[1].split('```')[0].strip()
                    
                result = json.loads(json_str)
                
                # Обрабатываем ошибки
                if 'errors' in result:
                    result['errors'] = process_error_positions(text_for_analysis, result['errors'])
                
                return result
            except json.JSONDecodeError:
                # Если не удалось извлечь JSON, возвращаем ошибку
                return {
                    "error": "Не удалось получить структурированный ответ от API",
                    "raw_response": raw_response
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

def process_error_positions(text, errors):
    """
    Обрабатывает массив ошибок и добавляет позиции в тексте
    
    Args:
        text: Исходный текст документа
        errors: Массив ошибок от Gemini
        
    Returns:
        list: Массив ошибок с добавленными позициями
    """
    processed_errors = []
    
    for error in errors:
        quote = error.get('quote', '')
        if not quote:
            continue
            
        # Ищем цитату в тексте
        position = find_text_position(text, quote)
        
        if position:
            error['start_pos'] = position['start']
            error['end_pos'] = position['end']
            error['found'] = True
        else:
            # Пытаемся найти похожий фрагмент
            similar_pos = find_similar_text(text, quote)
            if similar_pos:
                error['start_pos'] = similar_pos['start']
                error['end_pos'] = similar_pos['end']
                error['found'] = True
                error['approximate'] = True
            else:
                error['found'] = False
        
        processed_errors.append(error)
    
    return processed_errors

def find_text_position(text, quote):
    """
    Находит точную позицию цитаты в тексте
    
    Args:
        text: Исходный текст
        quote: Цитата для поиска
        
    Returns:
        dict: Позиции начала и конца или None
    """
    # Прямой поиск
    start = text.find(quote)
    if start != -1:
        return {"start": start, "end": start + len(quote)}
    
    # Поиск без учета регистра
    start = text.lower().find(quote.lower())
    if start != -1:
        return {"start": start, "end": start + len(quote)}
    
    return None

def find_similar_text(text, quote):
    """
    Находит похожий фрагмент текста (упрощенная версия)
    
    Args:
        text: Исходный текст
        quote: Цитата для поиска
        
    Returns:
        dict: Приблизительные позиции или None
    """
    # Разбиваем цитату на слова и ищем фрагмент с несколькими словами
    words = quote.split()
    if len(words) < 3:
        return None
    
    # Ищем фрагмент с первыми 3-5 словами
    search_fragment = ' '.join(words[:min(5, len(words))])
    start = text.lower().find(search_fragment.lower())
    
    if start != -1:
        # Приблизительно определяем конец
        estimated_end = start + len(quote)
        actual_end = min(estimated_end, len(text))
        return {"start": start, "end": actual_end}
    
    return None