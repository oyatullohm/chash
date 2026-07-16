from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.auth.models import Group
from .models import DiscountCardReport, CustomUser, Category, Notification
from .firebase_utils import send_push_notification
admin.site.unregister(Group)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "phone_number", "is_active", "discount_percent", "date_joined")
    search_fields = ("code", "full_name", "phone_number", "uid1c")
    list_filter = ("is_active", "discount_percent")
    ordering = ("-date_joined",)
    readonly_fields = ("uid1c", "code", "date_joined", "last_login")


@admin.register(DiscountCardReport)
class DiscountCardReportAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "discount_percent", "closing_balance", "created_at")
    search_fields = ("code", "full_name", "uid1c")
    list_filter = ("discount_percent",)
    ordering = ("-created_at",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("d_id", "name", "parent_id", "record_status_id", "created_at")
    search_fields = ("d_id", "name", "description")
    list_filter = ("record_status_id",)
# autocomplete_fields ni olib tashlang - agar parent_id oddiy IntegerField bo'lsa (FK emas), autocomplete ishlamaydi
    # autocomplete_fields = ("parent",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "target_display", "short_message", "is_sent", "sent_count", "failed_count", "created_at")
    search_fields = ("message", "recipient__code", "recipient__full_name", "recipient__phone_number")
    list_filter = ("is_sent",)
    autocomplete_fields = ("recipient",)  # qidiruv orqali bitta userni tanlash uchun
    readonly_fields = ("is_sent", "sent_count", "failed_count", "sent_at", "created_at")

    def target_display(self, obj):
        if obj.recipient:
            return obj.recipient.code
        return format_html('<b style="color:#d9534f;">HAMMAGA</b>')
    target_display.short_description = "Qabul qiluvchi"

    def short_message(self, obj):
        return obj.message[:60]
    short_message.short_description = "Xabar"

    def save_model(self, request, obj, form, change):
        # Avval oddiy saqlaymiz (yangi obyekt bo'lsa)
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new and not obj.is_sent:
            self._send_notification(obj)

    def _send_notification(self, notification: Notification):
        sent_count = 0
        failed_count = 0

        if notification.recipient:
            targets = [notification.recipient]
        else:
            targets = CustomUser.objects.filter(
                is_active=True
            ).exclude(firebase_key__isnull=True).exclude(firebase_key="")

        for user in targets:
            if not user.firebase_key:
                failed_count += 1
                continue
            try:
                send_push_notification(
                    firebase_key=user.firebase_key,
                    title="Bildirishnoma",
                    body=notification.message,
                )
                sent_count += 1
            except Exception:
                failed_count += 1

        notification.is_sent = True
        notification.sent_count = sent_count
        notification.failed_count = failed_count
        notification.sent_at = timezone.now()
        notification.save(update_fields=["is_sent", "sent_count", "failed_count", "sent_at"])