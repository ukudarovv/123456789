from django import forms
from leads.models import Lead
from dictionaries.models import City, Category
from catalog.models import School, Instructor


class LeadFilterForm(forms.Form):
    """Форма для фильтрации лидов"""
    status = forms.MultipleChoiceField(
        choices=Lead.LeadStatus.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
    )
    type = forms.ChoiceField(
        choices=[("", "Все типы")] + list(Lead.LeadType.choices),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True),
        required=False,
        empty_label="Все города",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label="Все категории",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.filter(is_active=True),
        required=False,
        empty_label="Все автошколы",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.filter(is_active=True),
        required=False,
        empty_label="Все инструкторы",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    language = forms.ChoiceField(
        choices=[("", "Все"), ("RU", "Русский"), ("KZ", "Қазақша")],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    source = forms.ChoiceField(
        choices=[("", "Все"), ("telegram_bot", "Telegram бот")],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Имя, телефон, ИИН, email, WhatsApp"}),
    )
    created_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    created_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )


class LeadStatusUpdateForm(forms.Form):
    """Форма для изменения статуса лида"""
    new_status = forms.ChoiceField(
        choices=Lead.LeadStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Комментарий (необязательно)"}),
    )

