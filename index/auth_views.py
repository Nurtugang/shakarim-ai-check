from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

def login_view(request):
    """
    Обработка входа пользователя
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Устанавливаем срок сессии, если пользователь хочет быть запомненным
            if not remember:
                # Сессия будет удалена при закрытии браузера
                request.session.set_expiry(0)
                
            # Перенаправляем на дашборд
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    
    return render(request, 'auth.html', {'form_type': 'login'})

def register_view(request):
    """
    Обработка регистрации пользователя
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Проверяем, что пароли совпадают
        if password != password2:
            messages.error(request, 'Пароли не совпадают.')
            return render(request, 'auth.html', {'form_type': 'register'})
        
        # Проверяем, что пользователь с таким именем не существует
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует.')
            return render(request, 'auth.html', {'form_type': 'register'})
        
        # Проверяем, что пользователь с такой почтой не существует
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с такой почтой уже существует.')
            return render(request, 'auth.html', {'form_type': 'register'})
        
        # Создаем пользователя
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Авторизуем пользователя
        login(request, user)
        
        # Перенаправляем на дашборд
        return redirect('dashboard')
    
    return render(request, 'auth.html', {'form_type': 'register'})

def logout_view(request):
    """
    Выход пользователя
    """
    logout(request)
    return redirect('index')