from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def login_view(request):
    """
    Обработка входа пользователя с интеграцией внешнего API
    """
    # Очищаем все предыдущие сообщения при GET запросе
    if request.method == 'GET':
        # Удаляем все сообщения из текущей сессии
        list(messages.get_messages(request))
    
    if request.method == 'POST':
        # Очищаем все предыдущие сообщения перед обработкой
        list(messages.get_messages(request))
        
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        remember = request.POST.get('remember')
        
        if not username or not password:
            messages.error(request, _('Введите логин и пароль.'))
            return render(request, 'auth.html', {'form_type': 'login'})
        
        # Используем кастомный backend для аутентификации
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Устанавливаем срок сессии, если пользователь хочет быть запомненным
            if not remember:
                # Сессия будет удалена при закрытии браузера
                request.session.set_expiry(0)
            
            # Перенаправляем на дашборд
            return redirect('index')
        else:
            # Добавляем только одно сообщение об ошибке
            messages.error(request, _('Неверный логин или пароль. Проверьте данные и попробуйте снова.'))
            logger.warning(f"Failed login attempt for username: {username}")
    
    return render(request, 'auth.html', {'form_type': 'login'})

def register_view(request):
    """
    Страница регистрации - теперь показывает информацию о том, что регистрация не нужна
    """
    # Очищаем сообщения при переходе на страницу регистрации
    if request.method == 'GET':
        list(messages.get_messages(request))
    
    # Поскольку теперь пользователи авторизуются через университетский API,
    # регистрация не требуется. Показываем информационную страницу.
    
    context = {
        'form_type': 'register',
        'api_registration': True  # Флаг для показа информации об API
    }
    
    return render(request, 'auth.html', context)

def logout_view(request):
    """
    Выход пользователя
    """
    user_name = request.user.get_full_name() if request.user.is_authenticated else None
    logout(request)
    
    # Очищаем все сообщения и добавляем прощание
    list(messages.get_messages(request))
    
    if user_name:
        messages.success(request, _('До свидания, {}!').format(user_name))
    
    return redirect('index')