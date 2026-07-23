from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import CustomUser


class Command(BaseCommand):
    help = "DiscountPercent jadvalidagi bir xil percent qiymatiga ega dublikat qatorlarni birlashtiradi"

    def handle(self, *args, **options):
        groups = defaultdict(list)
        for dp in DiscountPercent.objects.all():
            groups[dp.percent].append(dp)

        total_removed = 0

        with transaction.atomic():
            for percent, rows in groups.items():
                if len(rows) <= 1:
                    continue

                # Birinchisini "asosiy" (canonical) sifatida qoldiramiz
                canonical = rows[0]
                duplicates = rows[1:]

                for dup in duplicates:
                    moved = CustomUser.objects.filter(discount_percent=dup).update(
                        discount_percent=canonical
                    )
                    self.stdout.write(
                        f"percent={percent}: {moved} ta user {dup.id} -> {canonical.id} ga ko'chirildi"
                    )
                    dup.delete()
                    total_removed += 1

        self.stdout.write(self.style.SUCCESS(f"Tugadi. Jami o'chirilgan dublikatlar: {total_removed}"))