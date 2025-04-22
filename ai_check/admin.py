from django.contrib import admin
from .models import Check

@admin.register(Check)
class CheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'file_name', 'status', 'overall_score', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('file_name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'file_name', 'original_file', 'status')
        }),
        ('Текст документа', {
            'fields': ('extracted_text',),
            'classes': ('collapse',)
        }),
        ('Оценки', {
            'fields': ('structure_score', 'logic_score', 'grammar_score', 'originality_score', 'overall_score')
        }),
        ('Детальный анализ', {
            'fields': ('detailed_analysis', 'recommendations'),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        })
    )