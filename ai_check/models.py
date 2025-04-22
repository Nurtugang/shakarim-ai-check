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
        self.status = 'completed'
        self.save()