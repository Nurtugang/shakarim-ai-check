TOOLS = [{
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

def _get_analysis_tools():
    """Возвращает конфигурацию инструментов для Gemini API"""
    return TOOLS