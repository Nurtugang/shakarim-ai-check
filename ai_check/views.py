from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib import messages

import json
import os
import uuid
import logging

from .models import Check
from .utils.file_utils import process_document, save_uploaded_file
from .utils.gemini_service import analyze_document

logger = logging.getLogger(__name__)

def index(request):
    """Главная страница"""
    # Если пользователь уже залогинен, перенаправляем на дашборд
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

@login_required
def dashboard(request):
    """Дашборд пользователя с историей проверок"""
    user_checks = Check.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'checks': user_checks
    }
    return render(request, 'dashboard.html', context)

@login_required
def check_detail(request, check_id):
    """Детальная страница результатов проверки"""
    check = get_object_or_404(Check, id=check_id, user=request.user)
    
    # Распаковываем данные анализа для шаблона
    context = {
        'check': check,
    }
    
    if check.detailed_analysis:
        # Структура
        context['structure_analysis'] = check.detailed_analysis.get('structure', {}).get('analysis', '')
        context['structure_strengths'] = check.detailed_analysis.get('structure', {}).get('strengths', [])
        context['structure_weaknesses'] = check.detailed_analysis.get('structure', {}).get('weaknesses', [])
        
        # Логика
        context['logic_analysis'] = check.detailed_analysis.get('logic', {}).get('analysis', '')
        context['logic_strengths'] = check.detailed_analysis.get('logic', {}).get('strengths', [])
        context['logic_weaknesses'] = check.detailed_analysis.get('logic', {}).get('weaknesses', [])
        
        # Грамматика
        context['grammar_analysis'] = check.detailed_analysis.get('grammar', {}).get('analysis', '')
        context['grammar_strengths'] = check.detailed_analysis.get('grammar', {}).get('strengths', [])
        context['grammar_weaknesses'] = check.detailed_analysis.get('grammar', {}).get('weaknesses', [])
        
        # Оригинальность
        context['originality_analysis'] = check.detailed_analysis.get('originality', {}).get('analysis', '')
        context['originality_strengths'] = check.detailed_analysis.get('originality', {}).get('strengths', [])
        context['originality_weaknesses'] = check.detailed_analysis.get('originality', {}).get('weaknesses', [])
    
    if check.recommendations:
        # Рекомендации
        context['general_recommendations'] = check.recommendations.get('general', [])
        context['structure_recommendations'] = check.recommendations.get('structure', [])
        context['logic_recommendations'] = check.recommendations.get('logic', [])
        context['grammar_recommendations'] = check.recommendations.get('grammar', [])
        context['originality_recommendations'] = check.recommendations.get('originality', [])
    
    return render(request, 'check_detail.html', context)

@login_required
def document_view(request, check_id):
    """Страница просмотра документа с результатами анализа бок о бок"""
    check = get_object_or_404(Check, id=check_id, user=request.user)
    print(f"Extracted text length: {len(check.extracted_text) if check.extracted_text else 0}")
    print(f"Errors count: {len(check.errors_analysis) if check.errors_analysis else 0}")
    # Распаковываем данные анализа для шаблона
    context = {
        'check': check,
    }
    
    if check.detailed_analysis:
        # Структура
        context['structure_analysis'] = check.detailed_analysis.get('structure', {}).get('analysis', '')
        context['structure_strengths'] = check.detailed_analysis.get('structure', {}).get('strengths', [])
        context['structure_weaknesses'] = check.detailed_analysis.get('structure', {}).get('weaknesses', [])
        
        # Логика
        context['logic_analysis'] = check.detailed_analysis.get('logic', {}).get('analysis', '')
        context['logic_strengths'] = check.detailed_analysis.get('logic', {}).get('strengths', [])
        context['logic_weaknesses'] = check.detailed_analysis.get('logic', {}).get('weaknesses', [])
        
        # Грамматика
        context['grammar_analysis'] = check.detailed_analysis.get('grammar', {}).get('analysis', '')
        context['grammar_strengths'] = check.detailed_analysis.get('grammar', {}).get('strengths', [])
        context['grammar_weaknesses'] = check.detailed_analysis.get('grammar', {}).get('weaknesses', [])
        
        # Оригинальность
        context['originality_analysis'] = check.detailed_analysis.get('originality', {}).get('analysis', '')
        context['originality_strengths'] = check.detailed_analysis.get('originality', {}).get('strengths', [])
        context['originality_weaknesses'] = check.detailed_analysis.get('originality', {}).get('weaknesses', [])
    
    if check.recommendations:
        # Рекомендации
        context['general_recommendations'] = check.recommendations.get('general', [])
        context['structure_recommendations'] = check.recommendations.get('structure', [])
        context['logic_recommendations'] = check.recommendations.get('logic', [])
        context['grammar_recommendations'] = check.recommendations.get('grammar', [])
        context['originality_recommendations'] = check.recommendations.get('originality', [])
    
    return render(request, 'document_view.html', context)

@login_required
@require_POST
def upload_document(request):
    """API для загрузки и анализа документа"""
    try:
        # Проверяем наличие файла
        if 'document' not in request.FILES:
            return JsonResponse({'error': 'Файл не был загружен'}, status=400)
            
        document = request.FILES['document']
        
        # Получаем системную инструкцию, если она есть
        system_instruction = request.POST.get('system_instruction', '')
        force_analyze = request.POST.get('force_analyze', 'false') == 'true'
        
        # Проверка размера файла (максимум 5MB)
        if document.size > 5 * 1024 * 1024:
            return JsonResponse({
                'error': f'Файл слишком большой ({document.size // 1024 // 1024} MB). Максимум 5 MB.'
            }, status=400)
        
        # Создаем запись в базе данных
        check = Check.objects.create(
            user=request.user,
            file_name=document.name,
            original_file=document,
            status='pending'
        )
        
        try:
            # Извлекаем текст из документа
            extracted_text = process_document(document)
            check.extracted_text = extracted_text
            check.save()
            
            # Предупреждение о большом размере текста
            if len(extracted_text) > 100000 and not force_analyze:
                return JsonResponse({
                    'status': 'warning',
                    'message': f'Документ содержит {len(extracted_text):,} символов (больше рекомендуемых 100,000). Текст будет сокращен для анализа.',
                    'char_count': len(extracted_text),
                    'check_id': check.id
                })
            
            # Отправляем текст на анализ в Gemini
            analysis_result = analyze_document(extracted_text, system_instruction)
            
            # Проверяем на наличие ошибок в результате
            if 'error' in analysis_result:
                check.status = 'failed'
                check.save()
                return JsonResponse({
                    'status': 'error',
                    'check_id': check.id,
                    'error': analysis_result.get('error')
                }, status=500)
                
            # Обновляем запись в базе данных
            check.set_scores(analysis_result)
            
            # Возвращаем успешный результат
            return JsonResponse({
                'status': 'success',
                'check_id': check.id,
                'scores': {
                    'structure': check.structure_score,
                    'logic': check.logic_score,
                    'grammar': check.grammar_score, 
                    'originality': check.originality_score,
                    'overall': check.overall_score
                },
                'errors_count': len(check.errors_analysis) if check.errors_analysis else 0
            })
            
        except ValueError as e:
            # Ошибка обработки файла
            check.status = 'failed'
            check.save()
            return JsonResponse({'error': str(e)}, status=400)
            
        except Exception as e:
            # Общая ошибка
            logger.error(f"Error processing document: {str(e)}")
            check.status = 'failed'
            check.save()
            return JsonResponse({'error': 'Произошла ошибка при обработке документа'}, status=500)
            
    except Exception as e:
        # Общая ошибка
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': 'Произошла непредвиденная ошибка'}, status=500)

@login_required
def user_checks(request):
    """API для получения списка проверок пользователя"""
    checks = Check.objects.filter(user=request.user).order_by('-created_at')
    
    checks_data = []
    for check in checks:
        # Получаем статистику ошибок
        errors_summary = check.get_errors_summary()
        
        checks_data.append({
            'id': check.id,
            'file_name': check.file_name,
            'status': check.status,
            'created_at': check.created_at.strftime('%d.%m.%Y %H:%M'),
            'overall_score': check.overall_score,
            'errors_count': errors_summary.get('total', 0)
        })
    
    return JsonResponse({'checks': checks_data})

@login_required
def delete_check(request, check_id):
    """Удаление проверки"""
    check = get_object_or_404(Check, id=check_id, user=request.user)
    
    # Удаляем файл
    if check.original_file:
        check.original_file.delete()
    
    # Удаляем запись
    check.delete()
    
    return JsonResponse({'status': 'success'})