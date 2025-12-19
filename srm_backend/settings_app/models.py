from django.db import models


class ProjectSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value_json = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_setting"

    def __str__(self):
        return self.key


class WhatsAppTemplate(models.Model):
    class Scope(models.TextChoices):
        SCHOOL_CLIENT_MESSAGE = "SCHOOL_CLIENT_MESSAGE", "School client"
        INSTRUCTOR_CLIENT_MESSAGE = "INSTRUCTOR_CLIENT_MESSAGE", "Instructor client"
        TESTS_OWNER_MESSAGE = "TESTS_OWNER_MESSAGE", "Tests owner"

    scope = models.CharField(max_length=50, choices=Scope.choices)
    language = models.CharField(max_length=2)
    template_text = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "whatsapp_template"
        unique_together = ("scope", "language")

    def __str__(self):
        return f"{self.scope} ({self.language})"
    
    def render(self, **kwargs) -> str:
        """Рендеринг шаблона с переменными"""
        text = self.template_text
        for key, value in kwargs.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

