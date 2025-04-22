from django.urls import path
from . import views

urlpatterns = [
    # Основные страницы
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("check/<int:check_id>/", views.check_detail, name="check_detail"),
    path("document/<int:check_id>/", views.document_view, name="document_view"),
    path("api/upload-document/", views.upload_document, name="upload_document"),
    path("api/user-checks/", views.user_checks, name="user_checks"),
    path("api/delete-check/<int:check_id>/", views.delete_check, name="delete_check"),
]
