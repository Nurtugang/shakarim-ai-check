import os
import docx
import PyPDF2
import io
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging
from pdf2docx import Converter
import tempfile

logger = logging.getLogger(__name__)

def extract_text_from_docx(file):
    """
    Извлекает текст из файла DOCX
    
    Args:
        file: Django UploadedFile объект
        
    Returns:
        str: Извлеченный текст
    """
    # Сбрасываем указатель файла в начало
    file.seek(0)
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

def is_scanned_pdf(text):
    """
    Проверяет, является ли PDF сканированным документом
    
    Args:
        text: Извлеченный текст из PDF
        
    Returns:
        bool: True если PDF похож на сканированный документ
    """
    # Если текст пустой или содержит очень мало символов
    if not text or len(text.strip()) < 50:
        return True
        
    # Если текст содержит много пробелов или переносов строк
    if text.count('\n') > len(text) * 0.5:
        return True
        
    # Если текст содержит много специальных символов
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if special_chars > len(text) * 0.3:
        return True
        
    return False

def extract_text_from_pdf(file):
    """
    Извлекает текст из файла PDF через конвертацию в DOCX
    
    Args:
        file: Django UploadedFile объект
        
    Returns:
        str: Извлеченный текст
        
    Raises:
        ValueError: Если PDF является сканированным документом или не может быть прочитан
    """
    try:
        logger.info(f"Starting PDF processing for file: {file.name}, size: {file.size}")
        
        # Создаем временные файлы для PDF и DOCX
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_temp:
            # Сохраняем PDF во временный файл
            for chunk in file.chunks():
                pdf_temp.write(chunk)
            pdf_path = pdf_temp.name
            
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        try:
            # Конвертируем PDF в DOCX
            logger.info("Converting PDF to DOCX")
            cv = Converter(pdf_path)
            cv.convert(docx_path)
            cv.close()
            logger.info("PDF to DOCX conversion completed")
            
            # Открываем DOCX и извлекаем текст
            logger.info("Extracting text from DOCX")
            doc = docx.Document(docx_path)
            text = []
            
            # Извлекаем текст из параграфов
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)
            
            # Извлекаем текст из таблиц
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text.append(cell.text)
            
            full_text = '\n'.join(text)
            logger.info(f"Successfully extracted text, length: {len(full_text)}")
            
            # Проверяем, не является ли PDF сканированным документом
            if is_scanned_pdf(full_text):
                logger.error("PDF appears to be a scanned document")
                raise ValueError("Этот PDF-файл является сканированным документом. Пожалуйста, загрузите PDF с текстовым содержимым.")
            
            if not full_text.strip():
                logger.error("No text content extracted from PDF")
                raise ValueError("Не удалось извлечь текст из PDF файла. Возможно, это сканированный документ или файл поврежден.")
            
            return full_text
            
        finally:
            # Удаляем временные файлы
            try:
                os.unlink(pdf_path)
                os.unlink(docx_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary files: {str(e)}")
        
    except ValueError as e:
        # Пробрасываем ValueError дальше
        raise
    except Exception as e:
        # Логируем неожиданные ошибки
        logger.error(f"Unexpected error processing PDF: {str(e)}", exc_info=True)
        raise ValueError(f"Ошибка при обработке PDF файла: {str(e)}")

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