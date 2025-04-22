from django.urls import path
from .views import index, instructions, contacts
from . import auth_views

urlpatterns = [
    path("", index, name="index"),
    path("login/", auth_views.login_view, name="login"),
    path("register/", auth_views.register_view, name="register"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("instructions/", instructions, name="instructions"),
    path("contacts/", contacts, name="contacts"),
]