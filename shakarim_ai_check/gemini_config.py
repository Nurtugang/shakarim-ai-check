import os
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def ask_gemini(
    question: str,
    system_instruction: str = "",
    model_name: str = "gemini-2.0-flash",
    temperature: float = 0.2,
    max_output_tokens: int = 300,
    tools: dict = None
):
    """
    Гибкий запрос к Gemini API с настройками.
    
    :param question: Вопрос от пользователя
    :param system_instruction: Дополнительная инструкция для системы
    :param model_name: Название модели
    :param temperature: Контроль креативности (0 - точность, 2 - креативность)
    :param max_output_tokens: Максимальная длина ответа
    :param tools: Дополнительные инструменты (например, Function Calling)
    :return: Ответ от Gemini
    """

    try:
        prompt = f"{system_instruction}\n\nВопрос: {question}" if system_instruction else question
        
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                system_instruction=system_instruction,
                tools=tools
            )
        )
        
        return response.text

    except Exception as e:
        return f"Ошибка при запросе к Gemini: {str(e)}"