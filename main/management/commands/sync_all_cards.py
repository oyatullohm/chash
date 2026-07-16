from django.core.management.base import BaseCommand

from main.models import CustomUser
from main.Trasaciton import (
    sync_card_transactions,
    CardNotFoundError,
    Card1CApiError,
)


class Command(BaseCommand):
    help = "Barcha CustomUser lar uchun 1C'dan tranzaksiyalarni sinxronlaydi"

    def handle(self, *args, **options):
        users = CustomUser.objects.all()
        total = users.count()

        success_count = 0
        not_found_count = 0
        error_count = 0

        for index, user in enumerate(users, start=1):
            try:
                sync_card_transactions(card_code=user.code)
                success_count += 1
                self.stdout.write(f"[{index}/{total}] OK: {user.code}")
            except CardNotFoundError:
                not_found_count += 1
                self.stdout.write(self.style.WARNING(f"[{index}/{total}] Topilmadi: {user.code}"))
            except Card1CApiError as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"[{index}/{total}] Xato: {user.code} - {e}"))
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"[{index}/{total}] Kutilmagan xato: {user.code} - {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nTugadi. Jami: {total}, muvaffaqiyatli: {success_count}, "
            f"topilmadi: {not_found_count}, xato: {error_count}"
        ))
        
        
        