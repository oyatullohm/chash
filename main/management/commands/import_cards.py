import json
import re

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import CustomUser, DiscountPercent

# Kod aynan 13 xonali raqamdan iborat bo'lishi kerak (masalan "7802013700020")
CODE_PATTERN = re.compile(r"^\d{13}$")


def parse_dt(value: str):
    """ISO datetime satrini datetime obyektiga o'giradi, USE_TZ=True bo'lsa timezone-aware qiladi."""
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is None:
        return None
    if timezone.is_naive(dt) and timezone.get_current_timezone() is not None:
        try:
            dt = timezone.make_aware(dt)
        except Exception:
            pass
    return dt


class Command(BaseCommand):
    help = "data.json fayldan diskont karta ma'lumotlarini CustomUser jadvaliga import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="data.json fayli yo'li")

    def handle(self, *args, **options):
        json_path = options["json_path"]

        with open(json_path, "r", encoding="utf-8") as f:
            cards = json.load(f)

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for item in cards:
            code = (item.get("code") or "").strip()

            # Kod formatga mos kelmasa (13 xonali raqam emas) - o'tkazib yuboramiz
            if not CODE_PATTERN.match(code):
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f"O'tkazib yuborildi (code noto'g'ri format): {code!r}")
                )
                continue

            phone_number = (item.get("phoneNumber") or "").strip()
            username = phone_number if phone_number else code

            discount_percent_value = item.get("discountPercent", 0) or 0
            discount_percent_obj = DiscountPercent.objects.filter(
                percent=discount_percent_value
            ).order_by("id").first()
            if discount_percent_obj is None:
                discount_percent_obj = DiscountPercent.objects.create(
                    percent=discount_percent_value
                )

            defaults = {
                "username": username,
                "last_name": item.get("lastName", ""),
                "first_name": item.get("firstName", ""),
                "middle_name": item.get("middleName", ""),
                "full_name": item.get("fullName", ""),
                "discount_percent": discount_percent_obj,
                "expiry_date": parse_dt(item.get("expiryDate")),
                "registration_date": parse_dt(item.get("registrationDate")),
                "birth_date": parse_dt(item.get("birthDate")),
                "is_active": item.get("isActive", True),
                "registration": item.get("registration", False),
                "address": item.get("address", ""),
                "phone_number": phone_number,
            }

            # username boshqa (boshqa code'ga tegishli) userda band bo'lsa - pass
            username_taken = (
                CustomUser.objects
                .filter(username=username)
                .exclude(code=code)
                .exists()
            )
            if username_taken:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f"O'tkazib yuborildi (username band): {username!r} (code={code})")
                )
                continue

            user, created = CustomUser.objects.update_or_create(
                code=code,
                defaults=defaults,
            )

            if created or not user.uid1c:
                user.uid1c = item["uid1c"]

            if created:
                user.set_unusable_password()
                created_count += 1
            else:
                updated_count += 1

            user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Tugadi. Yaratildi: {created_count}, yangilandi: {updated_count}, "
                f"o'tkazib yuborildi: {skipped_count}"
            )
        )