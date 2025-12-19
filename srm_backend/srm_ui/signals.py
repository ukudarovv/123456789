from django.db.models.signals import post_save
from django.dispatch import receiver

from leads.models import Lead, LeadStatusHistory
from accounts.models import SrmUser
from .models import Notification


@receiver(post_save, sender=Lead)
def create_lead_notification(sender, instance, created, **kwargs):
    """Создать уведомления для менеджеров при создании нового лида"""
    if created:
        # Создаем уведомления для всех администраторов и владельцев
        admins = SrmUser.objects.filter(
            role__in=[SrmUser.Roles.ADMIN, SrmUser.Roles.OWNER]
        )
        
        for admin in admins:
            # Для ADMIN и OWNER создаем уведомление для всех лидов
            Notification.objects.create(
                user=admin,
                lead=instance,
                notification_type=Notification.NotificationType.NEW_LEAD,
            )
        
        # Для SCHOOL_MANAGER создаем уведомление только если лид относится к его школе
        school_managers = SrmUser.objects.filter(
            role=SrmUser.Roles.SCHOOL_MANAGER,
            school=instance.school
        )
        
        for manager in school_managers:
            if manager.school and instance.school == manager.school:
                Notification.objects.create(
                    user=manager,
                    lead=instance,
                    notification_type=Notification.NotificationType.NEW_LEAD,
                )


@receiver(post_save, sender=LeadStatusHistory)
def create_status_change_notification(sender, instance, created, **kwargs):
    """Создать уведомление при изменении статуса лида"""
    if created and instance.changed_by_user:
        # Создаем уведомление для всех администраторов и владельцев, кроме того, кто изменил статус
        admins = SrmUser.objects.filter(
            role__in=[SrmUser.Roles.ADMIN, SrmUser.Roles.OWNER]
        ).exclude(id=instance.changed_by_user.id)
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                lead=instance.lead,
                notification_type=Notification.NotificationType.STATUS_CHANGED,
            )
        
        # Для SCHOOL_MANAGER создаем уведомление только если лид относится к его школе
        school_managers = SrmUser.objects.filter(
            role=SrmUser.Roles.SCHOOL_MANAGER,
            school=instance.lead.school
        ).exclude(id=instance.changed_by_user.id)
        
        for manager in school_managers:
            if manager.school and instance.lead.school == manager.school:
                Notification.objects.create(
                    user=manager,
                    lead=instance.lead,
                    notification_type=Notification.NotificationType.STATUS_CHANGED,
                )

