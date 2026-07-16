import json

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from main.models import Category


def parse_dt(value):
    if not value:
        return None
    return parse_datetime(value)


class Command(BaseCommand):
    help = "a.json faylini Category jadvaliga import qiladi (id -> d_id, qolganlari 1:1)"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="a.json fayli yo'li")

    def handle(self, *args, **options):
        with open(options["json_path"], "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])

        created_count = 0
        updated_count = 0
        parent_missing = []

        # 1-bosqich: hammasini parent'siz (yoki mavjud parent bilan) yozamiz
        for item in items:
            parent_id = item.get("parent_id")
            parent_exists = (
                parent_id is not None
                and Category.objects.filter(d_id=parent_id).exists()
            )

            obj, created = Category.objects.update_or_create(
                d_id=item["id"],
                defaults={
                    "author_id": item.get("author_id", 0),
                    "initiator_id": item.get("initiator_id", 0),
                    "created_at": parse_dt(item.get("created_at")),
                    "updated_at": parse_dt(item.get("updated_at")),
                    "parent_id": parent_id if parent_exists else None,
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "record_status_id": item.get("record_status_id", 200),
                },
            )

            if not parent_exists and parent_id is not None:
                parent_missing.append((item["id"], parent_id))

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tugadi. Yaratildi: {created_count}, yangilandi: {updated_count}"
        ))

        if parent_missing:
            self.stdout.write(self.style.WARNING(
                f"\n{len(parent_missing)} ta yozuvda parent hali DB'da topilmadi "
                f"(parent bo'sh qoldirildi, keyinroq parent import qilinganda qayta ishga tushiring):"
            ))
            for d_id, parent_id in parent_missing:
                self.stdout.write(f"  d_id={d_id} -> parent_id={parent_id} (topilmadi)")