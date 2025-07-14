from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

import logging

from .models import Check
from .utils.file_utils import process_document
from .utils.gemini_service import analyze_document

logger = logging.getLogger('ai_check')

def index(request):
    """Главная страница"""
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
def document_view(request, check_id):
    """Страница просмотра документа с результатами анализа бок о бок"""
    check = get_object_or_404(Check, id=check_id, user=request.user)
    print(f"Extracted text length: {len(check.extracted_text) if check.extracted_text else 0}")
    print(f"Extracted HTML length: {len(check.extracted_html) if check.extracted_html else 0}")
    print(f"Errors count: {len(check.errors_analysis) if check.errors_analysis else 0}")

    context = {
        'check': check,
        'document_html': check.extracted_html,
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
        if 'document' not in request.FILES:
            return JsonResponse({'error': 'Файл не был загружен'}, status=400)
            
        document = request.FILES['document']
        logger.info(f"Starting document processing: {document.name}, size: {document.size} bytes")
        
        system_instruction = request.POST.get('system_instruction', '')
        force_analyze = request.POST.get('force_analyze', 'false') == 'true'
        
        if document.size > 5 * 1024 * 1024:
            return JsonResponse({
                'error': f'Файл слишком большой ({document.size // 1024 // 1024} MB). Максимум 5 MB.'
            }, status=400)
        
        check = Check.objects.create(
            user=request.user,
            file_name=document.name,
            original_file=document,
            status='pending'
        )
        logger.info(f"Created check record with ID: {check.id}")
        
        document.seek(0)
        
        try:
            try:
                logger.info("Attempting to extract text and HTML from document")
                extracted_text, extracted_html = process_document(document)
                logger.info(f"Extracted text length: {len(extracted_text) if extracted_text else 0}")
                logger.info(f"Extracted HTML length: {len(extracted_html) if extracted_html else 0}")
                
                if not extracted_text or len(extracted_text.strip()) < 50:
                    logger.warning("Extracted text is too short or empty")
                    check.status = 'failed'
                    check.save()
                    return JsonResponse({
                        'error': 'Не удалось извлечь текст из документа. Возможно, это сканированный документ или файл поврежден.'
                    }, status=400)
            except ValueError as e:
                logger.error(f"ValueError during text extraction: {str(e)}")
                check.status = 'failed'
                check.save()
                return JsonResponse({
                    'error': str(e)
                }, status=400)
            except Exception as e:
                logger.error(f"Unexpected error during text extraction: {str(e)}")
                check.status = 'failed'
                check.save()
                return JsonResponse({
                    'error': f'Ошибка при извлечении текста: {str(e)}'
                }, status=400)
                
            check.extracted_text = extracted_text
            check.extracted_html = extracted_html
            check.save()
            logger.info("Text successfully extracted and saved")
            
            # Предупреждение о большом размере текста
            if len(extracted_text) > 1000000 and not force_analyze:
                logger.info(f"Text is too long ({len(extracted_text)} chars), showing warning")
                return JsonResponse({
                    'status': 'warning',
                    'message': _('Документ содержит {char_count:,} символов (больше рекомендуемых 100,000). Текст будет сокращен для анализа.').format(char_count=len(extracted_text)),
                    'char_count': len(extracted_text),
                    'check_id': check.id
                })
            
            # Отправляем текст на анализ в Gemini
            logger.info("Starting Gemini analysis")
            analysis_result = analyze_document(extracted_text, system_instruction, extracted_html)
            logger.info("Gemini analysis completed")
            
            # Проверяем на наличие ошибок в результате
            if 'error' in analysis_result:
                logger.error(f"Error in Gemini analysis: {analysis_result.get('error')}")
                check.status = 'failed'
                check.save()
                return JsonResponse({
                    'status': 'error',
                    'check_id': check.id,
                    'error': analysis_result.get('error')
                }, status=500)
                
            # Обновляем запись в базе данных
            logger.info("Updating check record with analysis results")
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
            logger.error(f"ValueError during document processing: {str(e)}")
            check.status = 'failed'
            check.save()
            return JsonResponse({'error': str(e)}, status=400)
            
        except Exception as e:
            # Общая ошибка
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            check.status = 'failed'
            check.save()
            return JsonResponse({'error': f'Произошла ошибка при обработке документа: {str(e)}'}, status=500)
            
    except Exception as e:
        # Общая ошибка
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Произошла непредвиденная ошибка: {str(e)}'}, status=500)

@login_required
def user_checks(request):
    """API для получения списка проверок пользователя"""
    checks = Check.objects.filter(user=request.user).order_by('-created_at')
    checks_data = []
    for check in checks:
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
    """ Удаление проверки и связанного файла """
    check = get_object_or_404(Check, id=check_id, user=request.user)
    if check.original_file:
        check.original_file.delete()
    check.delete()
    return JsonResponse({'status': 'success'})


@login_required
def check_detail(request, check_id):
    """Детальная страница результатов проверки"""
    check = get_object_or_404(Check, id=check_id, user=request.user)
    
    context = {
        'check': check,
        'document_html': check.extracted_html
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