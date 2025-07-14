from django.db import models
from django.contrib.auth.models import User
import json

class Check(models.Model):
    """Модель для хранения результатов проверки документа"""
    
    STATUS_CHOICES = (
        ('pending', 'В обработке'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checks')
    file_name = models.CharField(max_length=255, verbose_name="Имя файла")
    original_file = models.FileField(upload_to='original_files/%Y/%m/%d/', verbose_name="Исходный файл")
    extracted_text = models.TextField(blank=True, null=True, verbose_name="Извлеченный текст")
    extracted_html = models.TextField(blank=True, null=True, verbose_name="Извлеченный HTML")
    
    # Результаты проверки
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    structure_score = models.FloatField(null=True, blank=True, verbose_name="Оценка структуры")
    logic_score = models.FloatField(null=True, blank=True, verbose_name="Оценка логики")
    grammar_score = models.FloatField(null=True, blank=True, verbose_name="Оценка грамматики")
    originality_score = models.FloatField(null=True, blank=True, verbose_name="Оценка оригинальности")
    overall_score = models.FloatField(null=True, blank=True, verbose_name="Общая оценка")
    
    # JSON-поля для хранения детального анализа
    detailed_analysis = models.JSONField(null=True, blank=True, verbose_name="Детальный анализ")
    recommendations = models.JSONField(null=True, blank=True, verbose_name="Рекомендации")
    errors_analysis = models.JSONField(null=True, blank=True, verbose_name="Анализ ошибок")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    def __str__(self):
        return f"Проверка {self.file_name} ({self.get_status_display()})"
    
    def set_scores(self, analysis_result):
        """Устанавливает оценки из результата анализа"""
        if not analysis_result:
            return
            
        self.structure_score = analysis_result.get('structure', {}).get('score')
        self.logic_score = analysis_result.get('logic', {}).get('score')
        self.grammar_score = analysis_result.get('grammar', {}).get('score')
        self.originality_score = analysis_result.get('originality', {}).get('score')
        
        # Вычисляем общую оценку как среднее арифметическое
        scores = [
            self.structure_score or 0,
            self.logic_score or 0,
            self.grammar_score or 0,
            self.originality_score or 0
        ]
        
        if any(scores):
            self.overall_score = sum(scores) / len([s for s in scores if s is not None])
        
        # Сохраняем детальный анализ и рекомендации
        self.detailed_analysis = analysis_result
        self.recommendations = analysis_result.get('recommendations', {})
        
        # Сохраняем анализ ошибок (НОВОЕ)
        self.errors_analysis = analysis_result.get('errors', [])
        
        self.status = 'completed'
        self.save()
    
    def get_errors_by_type(self, error_type=None):
        """
        Возвращает ошибки по типу
        
        Args:
            error_type: Тип ошибки (grammar, style, logic, structure, originality) или None для всех
            
        Returns:
            list: Список ошибок
        """
        if not self.errors_analysis:
            return []
        
        errors = self.errors_analysis
        if error_type:
            errors = [error for error in errors if error.get('error_type') == error_type]
        
        return errors
    
    def get_errors_summary(self):
        """
        Возвращает сводку по ошибкам
        
        Returns:
            dict: Статистика по типам ошибок
        """
        if not self.errors_analysis:
            return {}
        
        summary = {
            'total': len(self.errors_analysis),
            'by_type': {},
            'by_severity': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        for error in self.errors_analysis:
            error_type = error.get('error_type', 'unknown')
            severity = error.get('severity', 'medium')
            
            summary['by_type'][error_type] = summary['by_type'].get(error_type, 0) + 1
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
        
        return summary