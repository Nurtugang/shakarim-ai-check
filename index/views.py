from django.utils.translation import gettext as _
from django.shortcuts import render, redirect
from django.db.models import Avg, Count
from ai_check.models import Check
from .models import ContactMessage
from django.contrib import messages

def index(request):
    """Главная страница с персонализацией для авторизованных пользователей"""
    context = {}
    
    # Если пользователь авторизован, добавляем статистику
    if request.user.is_authenticated:
        user_checks = Check.objects.filter(user=request.user)
        
        # Определяем тип авторизации
        auth_type = request.session.get('auth_type', 'unknown')
        auth_source = request.session.get('auth_source', 'local')
        
        # Дополнительная проверка для старых пользователей
        if auth_type == 'unknown':
            # Если пароль неиспользуемый, скорее всего это API пользователь
            if not request.user.has_usable_password():
                auth_type = 'api'
                auth_source = 'platonus'
                # Сохраняем в сессию для будущих запросов
                request.session['auth_type'] = 'api'
                request.session['auth_source'] = 'platonus'
            else:
                auth_type = 'local'
                request.session['auth_type'] = 'local'
        
        # Статистика пользователя
        user_stats = {
            'total_checks': user_checks.count(),
            'avg_score': user_checks.filter(overall_score__isnull=False).aggregate(
                avg=Avg('overall_score')
            )['avg'],
            'last_check': user_checks.filter(status='completed').order_by('-created_at').first(),
            'auth_type': auth_type,
            'auth_source': auth_source
        }
        
        context['user_stats'] = user_stats
    
    return render(request, 'index.html', context)

def instructions(request):
    return render(request, 'instructions.html')

def contacts(request):
    if request.method == 'POST':
        ContactMessage.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message')
        )
        messages.success(request, _('Ваше сообщение успешно отправлено!'))
        return redirect('contacts')
    return render(request, 'contacts.html')