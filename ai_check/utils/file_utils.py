import os
import docx
import PyPDF2
import io
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def extract_text_from_docx(file):
    """
    Извлекает текст из файла DOCX
    
    Args:
        file: Django UploadedFile объект
        
    Returns:
        str: Извлеченный текст
    """
    doc = docx.Document(file)
    full_text = []
    
    # Извлекаем текст из всех параграфов
    for para in doc.paragraphs:
        full_text.append(para.text)
        
    # Извлекаем текст из таблиц
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    full_text.append(paragraph.text)
    
    return '\n'.join(full_text)

def extract_text_from_pdf(file):
    """
    Извлекает текст из файла PDF
    
    Args:
        file: Django UploadedFile объект
        
    Returns:
        str: Извлеченный текст
    """
    # Создаем байтовый объект из файла
    file_data = file.read()
    
    # Создаем объект PdfReader
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
    
    # Извлекаем текст из всех страниц
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    
    return text

def save_uploaded_file(uploaded_file, user_id):
    """
    Сохраняет загруженный файл в медиа-директорию
    
    Args:
        uploaded_file: Django UploadedFile объект
        user_id: ID пользователя
        
    Returns:
        str: Путь к сохраненному файлу
    """
    # Создаем путь для сохранения файла
    file_name = uploaded_file.name
    file_path = f'uploads/{user_id}/{file_name}'
    
    # Сохраняем файл
    path = default_storage.save(file_path, ContentFile(uploaded_file.read()))
    
    # Возвращаем путь к файлу
    return path

def get_file_extension(file_name):
    """
    Получает расширение файла
    
    Args:
        file_name: Имя файла
        
    Returns:
        str: Расширение файла в нижнем регистре
    """
    _, extension = os.path.splitext(file_name)
    return extension.lower()[1:]  # Удаляем точку

def process_document(file):
    """
    Обрабатывает загруженный документ и извлекает из него текст
    
    Args:
        file: Django UploadedFile объект
        
    Returns:
        str: Извлеченный текст
        
    Raises:
        ValueError: Если формат файла не поддерживается
    """
    file_ext = get_file_extension(file.name)
    
    if file_ext == 'pdf':
        return extract_text_from_pdf(file)
    elif file_ext in ['docx', 'doc']:
        return extract_text_from_docx(file)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {file_ext}. Поддерживаются только PDF и DOCX.")