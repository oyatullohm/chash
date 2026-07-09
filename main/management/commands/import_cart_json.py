import json
import uuid

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from main.models import DiscountCardReport, DiscountCardTransaction

# Deterministik UUID yaratish uchun sobit namespace
# (bir xil hujjat har doim bir xil docguid olishi uchun)
DOC_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def parse_dt(value):
    if not value:
        return None
    return parse_datetime(value)


def make_docguid(code: str, doc_number: str, doc_date, row_number: int) -> uuid.UUID:
    key = f"{code}|{doc_number}|{doc_date}|{row_number}"
    return uuid.uuid5(DOC_NAMESPACE, key)


class Command(BaseCommand):
    help = "cart.json faylini DiscountCardReport va DiscountCardTransaction jadvallariga import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="cart.json fayli yo'li")

    def handle(self, *args, **options):
        with open(options["json_path"], "r", encoding="utf-8") as f:
            reports_data = json.load(f)

        report_created = 0
        report_updated = 0
        tx_created = 0
        tx_updated = 0

        for item in reports_data:
            report, created = DiscountCardReport.objects.update_or_create(
                uid1c=item["uid1c"],
                defaults={
                    "code": item.get("code", ""),
                    "full_name": item.get("fullName", ""),
                    "discount_percent": item.get("discountPercent", 0) or 0,
                    "period_from": parse_dt(item.get("periodFrom")),
                    "period_to": parse_dt(item.get("periodTo")),
                    "opening_balance": item.get("openingBalance", 0) or 0,
                    "total_income": item.get("totalIncome", 0) or 0,
                    "total_expense": item.get("totalExpense", 0) or 0,
                    "closing_balance": item.get("closingBalance", 0) or 0,
                },
            )
            if created:
                report_created += 1
            else:
                report_updated += 1

            for t in item.get("transactions", []):
                doc_date = parse_dt(t.get("docDate"))
                docguid = make_docguid(
                    report.code, t.get("docNumber", ""), t.get("docDate"), t.get("rowNumber", 0)
                )

                tx, tx_is_created = DiscountCardTransaction.objects.update_or_create(
                    docguid=docguid,
                    defaults={
                        "code": report,
                        "row_number": t.get("rowNumber", 0),
                        "doc_presentation": t.get("docPresentation", ""),
                        "doc_number": t.get("docNumber", ""),
                        "doc_date": doc_date,
                        "opening_balance": t.get("openingBalance", 0) or 0,
                        "income": t.get("income", 0) or 0,
                        "expense": t.get("expense", 0) or 0,
                        "closing_balance": t.get("closingBalance", 0) or 0,
                    },
                )
                if tx_is_created:
                    tx_created += 1
                else:
                    tx_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Reportlar: {report_created} yaratildi, {report_updated} yangilandi. "
            f"Tranzaksiyalar: {tx_created} yaratildi, {tx_updated} yangilandi."
        ))