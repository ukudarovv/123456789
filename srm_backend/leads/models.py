import uuid
from django.conf import settings
from django.db import models

from botusers.models import BotUser
from catalog.models import School, Instructor, InstructorTariff
from dictionaries.models import City, Category, TrainingFormat, TrainingTimeSlot


class Lead(models.Model):
    class LeadType(models.TextChoices):
        SCHOOL = "SCHOOL", "School"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"
        TESTS = "TESTS", "Tests"

    class LeadStatus(models.TextChoices):
        NEW = "NEW", "New"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PAID = "PAID", "Paid"
        DONE = "DONE", "Done"
        CANCELED = "CANCELED", "Canceled"

    class Intent(models.TextChoices):
        NO_LICENSE = "NO_LICENSE", "No license"
        REFRESH = "REFRESH", "Refresh"
        CERT_NOT_PASSED = "CERT_NOT_PASSED", "Cert not passed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=LeadType.choices)
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW)
    bot_user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True)
    language = models.CharField(max_length=2)
    main_intent = models.CharField(max_length=30, choices=Intent.choices, null=True, blank=True)

    # School flow
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    training_format = models.ForeignKey(TrainingFormat, on_delete=models.SET_NULL, null=True, blank=True)
    training_time = models.ForeignKey(TrainingTimeSlot, on_delete=models.SET_NULL, null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    tariff_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название тарифа")
    tariff_price_kzt = models.IntegerField(null=True, blank=True)

    # Instructor flow
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True)
    instructor_tariff = models.ForeignKey(InstructorTariff, on_delete=models.SET_NULL, null=True, blank=True)
    instructor_tariff_price_kzt = models.IntegerField(null=True, blank=True)
    gearbox = models.CharField(max_length=10, null=True, blank=True)
    preferred_instructor_gender = models.CharField(max_length=1, null=True, blank=True)
    has_driver_license = models.BooleanField(null=True, blank=True)

    # Contacts
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    iin = models.CharField(max_length=12, null=True, blank=True)
    whatsapp = models.CharField(max_length=32, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    payment_link = models.URLField(null=True, blank=True)

    source = models.CharField(max_length=50, default="telegram_bot")
    utm_source = models.CharField(max_length=255, null=True, blank=True)
    utm_campaign = models.CharField(max_length=255, null=True, blank=True)
    utm_medium = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lead"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["type", "created_at"]),
            models.Index(fields=["school", "status", "created_at"]),
            models.Index(fields=["city", "created_at"]),
            models.Index(fields=["phone"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} - {self.name} ({self.phone})"


class LeadStatusHistory(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "lead_status_history"
        indexes = [
            models.Index(fields=["lead", "changed_at"]),
        ]
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.lead_id}: {self.old_status} -> {self.new_status}"

