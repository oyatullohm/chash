import time

from django.core.management.base import BaseCommand

from main.models import CustomUser
from main.Trasaciton import (
    sync_card_transactions,
    CardNotFoundError,
    Card1CApiError,
)

DELAY_BETWEEN_REQUESTS = 0.3  # har bir so'rovdan keyin kutish (soniya)
MAX_RETRIES_ON_ERROR = 3
RETRY_DELAY = 3  # xato bo'lsa, qayta urinishdan oldin kutish (soniya)


class Command(BaseCommand):
    help = "Barcha CustomUser lar uchun 1C'dan tranzaksiyalarni sinxronlaydi"

    def handle(self, *args, **options):
        users = CustomUser.objects.all()
        total = users.count()

        self.success_count = 0
        self.not_found_count = 0
        self.error_count = 0

        for index, user in enumerate(users, start=1):
            self._sync_with_retry(user, index, total)
            # time.sleep(DELAY_BETWEEN_REQUESTS)

        self.stdout.write(self.style.SUCCESS(
            f"\nTugadi. Jami: {total}, muvaffaqiyatli: {self.success_count}, "
            f"topilmadi: {self.not_found_count}, xato: {self.error_count}"
        ))

    def _sync_with_retry(self, user, index, total):
        for attempt in range(1, MAX_RETRIES_ON_ERROR + 1):
            try:
                sync_card_transactions(card_code=user.code)
                self.success_count += 1
                self.stdout.write(f"[{index}/{total}] OK: {user.code}")
                return
            except CardNotFoundError:
                self.not_found_count += 1
                self.stdout.write(self.style.WARNING(f"[{index}/{total}] Topilmadi: {user.code}"))
                return
            except Card1CApiError as e:
                if attempt < MAX_RETRIES_ON_ERROR:
                    self.stdout.write(self.style.WARNING(
                        f"[{index}/{total}] Xato (urinish {attempt}/{MAX_RETRIES_ON_ERROR}), "
                        f"{RETRY_DELAY}s kutib qayta urinilmoqda: {user.code}"
                    ))
                    time.sleep(RETRY_DELAY)
                    continue
                self.error_count += 1
                self.stdout.write(self.style.ERROR(
                    f"[{index}/{total}] Xato (barcha urinishlar tugadi): {user.code} - {e}"
                ))
                return
            except Exception as e:
                self.error_count += 1
                self.stdout.write(self.style.ERROR(f"[{index}/{total}] Kutilmagan xato: {user.code} - {e}"))
                return