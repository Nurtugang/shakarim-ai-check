import re

def get_list_info(paragraph):
    """
    Определяет информацию о списке для параграфа
    
    Args:
        paragraph: Параграф из python-docx
        
    Returns:
        dict: Информация о списке
    """
    try:
        # Проверяем стиль параграфа
        style_name = paragraph.style.name.lower()
        
        # Определяем по стилю
        if 'list bullet' in style_name or 'list paragraph' in style_name:
            return {
                'is_list': True,
                'is_numbered': False,
                'level': extract_level_from_style(style_name)
            }
        elif 'list number' in style_name:
            return {
                'is_list': True,
                'is_numbered': True,
                'level': extract_level_from_style(style_name)
            }
        
        # Проверяем через paragraph format
        if hasattr(paragraph, '_element') and paragraph._element is not None:
            # Ищем маркеры списка в тексте
            text = paragraph.text.strip()
            if text:
                # Простая проверка на bullet points
                if text.startswith('•') or text.startswith('·') or text.startswith('-') or text.startswith('*'):
                    return {
                        'is_list': True,
                        'is_numbered': False,
                        'level': 0
                    }
                
                # Простая проверка на нумерованные списки
                import re
                if re.match(r'^\d+[\.\)]\s+', text):
                    return {
                        'is_list': True,
                        'is_numbered': True,
                        'level': 0
                    }
        
        return {
            'is_list': False,
            'is_numbered': False,
            'level': 0
        }
        
    except Exception:
        return {
            'is_list': False,
            'is_numbered': False,
            'level': 0
        }


def extract_level_from_style(style_name):
    """
    Извлекает уровень списка из названия стиля
    
    Args:
        style_name: Название стиля
        
    Returns:
        int: Уровень списка (0-based)
    """
    import re
    
    # Ищем цифры в названии стиля (List Bullet 2, List Number 3, etc.)
    match = re.search(r'(\d+)', style_name)
    if match:
        return int(match.group(1)) - 1  # Конвертируем в 0-based
    
    return 0
