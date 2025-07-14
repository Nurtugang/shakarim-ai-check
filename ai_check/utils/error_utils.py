import re
import json
import logging

logger = logging.getLogger('ai_check')


def process_error_positions(text, errors, html_content=None):
    """
    Обрабатывает массив ошибок и добавляет позиции в тексте и HTML
    
    Args:
        text: Исходный текст документа
        errors: Массив ошибок от Gemini
        html_content: HTML-версия документа (опционально)
        
    Returns:
        list: Массив ошибок с добавленными позициями
    """
    processed_errors = []
    
    for error in errors:
        quote = error.get('quote', '')
        if not quote:
            continue
            
        # Ищем цитату в обычном тексте (для совместимости)
        text_position = find_text_position(text, quote)
        
        if text_position:
            error['start_pos'] = text_position['start']
            error['end_pos'] = text_position['end']
            error['found'] = True
            
            # Если есть HTML - пытаемся найти позицию в HTML
            if html_content:
                html_position = find_position_in_html(html_content, quote, text_position)
                if html_position:
                    error['html_start'] = html_position['start']
                    error['html_end'] = html_position['end']
                    error['html_found'] = True
        else:
            # Пытаемся найти похожий фрагмент
            similar_pos = find_similar_text(text, quote)
            if similar_pos:
                error['start_pos'] = similar_pos['start']
                error['end_pos'] = similar_pos['end']
                error['found'] = True
                error['approximate'] = True
                
                # Пытаемся найти в HTML тоже
                if html_content:
                    html_position = find_position_in_html(html_content, quote, similar_pos)
                    if html_position:
                        error['html_start'] = html_position['start']
                        error['html_end'] = html_position['end']
                        error['html_found'] = True
                        error['html_approximate'] = True
            else:
                error['found'] = False
        
        processed_errors.append(error)
    
    return processed_errors


def find_position_in_html(html_content, quote, text_position):
    """
    Находит позицию цитаты в HTML, используя позицию из текста как ориентир
    
    Args:
        html_content: HTML-контент
        quote: Цитата для поиска
        text_position: Позиция в обычном тексте
        
    Returns:
        dict: Позиции в HTML или None
    """
    try:
        # Простой поиск точного совпадения в HTML
        html_start = html_content.find(quote)
        if html_start != -1:
            return {
                "start": html_start,
                "end": html_start + len(quote)
            }
        
        # Поиск без учета регистра
        html_start = html_content.lower().find(quote.lower())
        if html_start != -1:
            return {
                "start": html_start,
                "end": html_start + len(quote)
            }
        
        # Более сложный поиск - учитываем HTML-теги
        return find_quote_with_html_tags(html_content, quote)
        
    except Exception as e:
        logger.warning(f"Error finding position in HTML: {str(e)}")
        return None

def find_quote_with_html_tags(html_content, quote):
    """
    Ищет цитату в HTML, игнорируя HTML-теги внутри цитаты
    
    Args:
        html_content: HTML-контент
        quote: Цитата для поиска
        
    Returns:
        dict: Позиции или None
    """
    import re
    
    # Убираем HTML-теги из контента для поиска
    clean_html = re.sub(r'<[^>]+>', '', html_content)
    
    # Ищем цитату в очищенном HTML
    clean_start = clean_html.find(quote)
    if clean_start == -1:
        clean_start = clean_html.lower().find(quote.lower())
    
    if clean_start == -1:
        return None
    
    # Пытаемся найти соответствующую позицию в оригинальном HTML
    # Это приблизительный алгоритм
    char_count = 0
    html_pos = 0
    
    for i, char in enumerate(html_content):
        if char == '<':
            # Пропускаем HTML-тег
            tag_end = html_content.find('>', i)
            if tag_end != -1:
                html_pos = tag_end + 1
                continue
        
        if char_count == clean_start:
            # Нашли начальную позицию
            start_pos = html_pos
            # Ищем конечную позицию
            quote_chars_found = 0
            end_pos = start_pos
            
            for j in range(start_pos, len(html_content)):
                if html_content[j] == '<':
                    tag_end = html_content.find('>', j)
                    if tag_end != -1:
                        j = tag_end
                        continue
                
                if quote_chars_found < len(quote) and html_content[j].lower() == quote[quote_chars_found].lower():
                    quote_chars_found += 1
                    end_pos = j + 1
                    if quote_chars_found == len(quote):
                        break
            
            return {
                "start": start_pos,
                "end": end_pos
            }
        
        if char != '<':
            char_count += 1
        html_pos += 1
    
    return None

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

def find_last_complete_error(json_str, errors_start):
    """
    Находит позицию конца последней полной ошибки в JSON
    
    Args:
        json_str: JSON строка
        errors_start: Позиция начала массива errors
        
    Returns:
        int: Позиция конца последней полной ошибки или -1
    """
    try:
        # Ищем все закрывающие скобки объектов ошибок
        pos = errors_start
        last_complete_pos = -1
        brace_count = 0
        in_string = False
        escape_next = False
        
        while pos < len(json_str):
            char = json_str[pos]
            
            if escape_next:
                escape_next = False
                pos += 1
                continue
            
            if char == '\\':
                escape_next = True
                pos += 1
                continue
            
            if char == '"':
                in_string = not in_string
                pos += 1
                continue
            
            if in_string:
                pos += 1
                continue
            
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Нашли конец объекта ошибки
                    # Проверяем, что это действительно полная ошибка
                    if is_complete_error_object(json_str, errors_start, pos + 1):
                        last_complete_pos = pos + 1
            
            pos += 1
        
        return last_complete_pos
        
    except Exception as e:
        logger.error(f"Error finding last complete error: {str(e)}")
        return -1

def is_complete_error_object(json_str, start_pos, end_pos):
    """
    Проверяет, является ли фрагмент JSON полным объектом ошибки
    
    Args:
        json_str: JSON строка
        start_pos: Начальная позиция для проверки
        end_pos: Конечная позиция
        
    Returns:
        bool: True если объект полный
    """
    try:
        # Извлекаем фрагмент и пытаемся найти в нем требуемые поля
        fragment = json_str[start_pos:end_pos]
        
        # Проверяем наличие обязательных полей ошибки
        required_fields = ['"quote":', '"error_type":', '"description":', '"suggestion":', '"severity":']
        
        for field in required_fields:
            if field not in fragment:
                return False
        
        return True
        
    except Exception:
        return False
    
def fix_truncated_json(raw_text):
    """
    Пытается исправить обрезанный JSON ответ от Gemini
    
    Args:
        raw_text: Сырой текст ответа
        
    Returns:
        dict: Исправленный JSON или None если не удалось
    """
    try:
        logger.info("Attempting to fix truncated JSON response")
        
        # Извлекаем JSON из текста
        json_str = raw_text.strip()
        if json_str.startswith('```json'):
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif json_str.startswith('```'):
            json_str = json_str.split('```')[1].split('```')[0].strip()
        
        # Очищаем от управляющих символов
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
        json_str = json_str.replace('\t', ' ')
        
        logger.info(f"Original JSON length: {len(json_str)}")
        
        # Находим последнюю корректную позицию в массиве errors
        errors_start = json_str.find('"errors": [')
        if errors_start == -1:
            logger.warning("Could not find errors array in JSON")
            return None
        
        # Ищем последнюю полную ошибку
        last_complete_error_end = find_last_complete_error(json_str, errors_start)
        
        if last_complete_error_end == -1:
            logger.warning("Could not find any complete errors")
            return None
        
        # Обрезаем JSON до последней полной ошибки и закрываем структуру
        fixed_json = json_str[:last_complete_error_end] + ']}'
        
        logger.info(f"Fixed JSON length: {len(fixed_json)}")
        
        # Пытаемся распарсить исправленный JSON
        result = json.loads(fixed_json)
        
        logger.info(f"Successfully fixed JSON with {len(result.get('errors', []))} errors")
        return result
        
    except Exception as e:
        logger.error(f"Error fixing truncated JSON: {str(e)}")
        return None

