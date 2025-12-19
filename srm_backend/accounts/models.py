from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from catalog.models import School


class SrmUser(AbstractUser):
    class Roles(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        SCHOOL_MANAGER = "SCHOOL_MANAGER", "School Manager"

    role = models.CharField(max_length=32, choices=Roles.choices, default=Roles.ADMIN)
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True, help_text="Required for SCHOOL_MANAGER"
    )

    def clean(self):
        super().clean()
        if self.role == self.Roles.SCHOOL_MANAGER and not self.school:
            raise models.ValidationError("school is required for SCHOOL_MANAGER role")

    class Meta:
        db_table = "srm_user"

    def __str__(self):
        return f"{self.username} ({self.role})"

