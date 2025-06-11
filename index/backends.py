import requests
import json
import logging
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.conf import settings

logger = logging.getLogger(__name__)

class ExternalAPIBackend(BaseBackend):
    """
    Кастомный backend для аутентификации через внешний API университета
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Аутентификация пользователя через внешний API
        """
        if username is None or password is None:
            return None
        
        # Сначала пробуем внешний API
        user = self._authenticate_via_external_api(username, password, request)
        if user:
            return user
        
        # Если внешний API не сработал, пробуем стандартную Django аутентификацию
        # (для админов и тестовых пользователей)
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                # Помечаем как локальный вход
                if request:
                    request.session['auth_type'] = 'local'
                return user
        except User.DoesNotExist:
            pass
        
        return None
    
    def _authenticate_via_external_api(self, username, password, request=None):
        """
        Отправляет запрос к внешнему API для аутентификации
        """
        api_url = "https://apisdo.semgu.kz/apimobile/auth/login"
        
        try:
            # Отправляем POST запрос к API
            response = requests.post(
                api_url,
                json={
                    "login": username,
                    "password": password
                },
                timeout=10,  # Таймаут 10 секунд
                headers={'Content-Type': 'application/json'}
            )
            
            # Проверяем статус ответа
            if response.status_code != 200:
                logger.warning(f"External API returned status {response.status_code}")
                return None
            
            # Парсим JSON ответ
            data = response.json()
            
            # Проверяем успешность аутентификации
            if not data.get('success') or data.get('status') != 'success':
                logger.info(f"External API authentication failed for user {username}")
                return None
            
            # Извлекаем данные пользователя
            person_id = data.get('personid')
            firstname = data.get('firstname', '')
            lastname = data.get('lastname', '')
            patronymic = data.get('patronymic', '')
            
            if not person_id:
                logger.error("External API didn't return personid")
                return None
            
            # Создаем или обновляем пользователя в Django
            user = self._get_or_create_user(person_id, firstname, lastname, patronymic, api_auth=True)
            
            # ВАЖНО: Помечаем в сессии, что это API аутентификация
            if request:
                request.session['auth_type'] = 'api'
                request.session['auth_source'] = 'platonus'
            
            logger.info(f"Successfully authenticated user {username} via external API")
            return user
            
        except requests.RequestException as e:
            logger.error(f"Error connecting to external API: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in external API authentication: {str(e)}")
            return None
    
    def _get_or_create_user(self, person_id, firstname, lastname, patronymic, api_auth=False):
        """
        Создает нового пользователя или обновляет существующего
        """
        try:
            # Пытаемся найти существующего пользователя
            user = User.objects.get(username=person_id)
            
            # Обновляем данные пользователя
            user.first_name = firstname
            user.last_name = lastname
            
            # Если это API аутентификация, помечаем пользователя специальным паролем
            if api_auth:
                user.set_unusable_password()
            
            user.save()
            
            logger.info(f"Updated existing user {person_id}")
            
        except User.DoesNotExist:
            # Создаем нового пользователя
            user = User.objects.create_user(
                username=person_id,
                first_name=firstname,
                last_name=lastname,
                email=f"{person_id}@semgu.kz",  # Генерируем email на основе ID
                password=None  # Пароль не устанавливаем, так как аутентификация через внешний API
            )
            
            # Если это API аутентификация, делаем пароль неиспользуемым для Django аутентификации
            if api_auth:
                user.set_unusable_password()
            
            user.save()
            
            logger.info(f"Created new user {person_id} via API authentication")
        
        return user
    
    def get_user(self, user_id):
        """
        Получает пользователя по ID (требуется Django)
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None