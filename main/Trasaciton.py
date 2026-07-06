from datetime import datetime
import requests
from django.db import transaction
from .models import DiscountCardReport, DiscountCardTransaction
from django.conf import settings

BASE_URL = "http://test.ksbapps.uz:17777/afm/hs/discount_api/transactions"
LOGIN = settings.API_1C_LOGIN
PASSWORD = settings.API_1C_PASSWD


def parse_iso_datetime(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fetch_card_transactions(code: str, date_from: str = None, date_to: str = None) -> dict:
    params = {"code": code}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to

    response = requests.get(BASE_URL, params=params, auth=(LOGIN, PASSWORD), timeout=30)
    response.raise_for_status()
    return response.json()


def sync_card_transactions(code: str, date_from: str = None, date_to: str = None):
    """
    Tezlashtirilgan versiya:
      - Report: bitta update_or_create (o'zgarishsiz)
      - Transactions: bitta SELECT bilan mavjudlarini o'qiydi, so'ng faqat
        yangilarini bitta bulk_create bilan yozadi (N ta alohida so'rov o'rniga
        atigi 2 ta so'rov - 1 SELECT + 1 INSERT).
    """
    data = fetch_card_transactions(code, date_from, date_to)

    with transaction.atomic():
        code, created = DiscountCardReport.objects.update_or_create(
            code=data["code"],
            defaults={
                "uid1c": data["uid1c"],
                "full_name": data.get("fullName", ""),
                "discount_percent": data.get("discountPercent", 0),
                "period_from": parse_iso_datetime(data["periodFrom"]),
                "period_to": parse_iso_datetime(data["periodTo"]),
                "opening_balance": data.get("openingBalance", 0),
                "total_income": data.get("totalIncome", 0),
                "total_expense": data.get("totalExpense", 0),
                "closing_balance": data.get("closingBalance", 0),
            },
        )

        items = data.get("transactions", [])

        # 1) Mavjud tranzaksiyalarning kalitlarini BITTA so'rov bilan olamiz
        existing_keys = set(
            DiscountCardTransaction.objects
            .filter(code=code)
            .values_list("doc_number", "doc_date", "row_number")
        )

        # 2) Faqat bazada yo'q bo'lganlarini tayyorlaymiz
        new_objects = []
        for item in items:
            doc_date = parse_iso_datetime(item["docDate"])
            key = (item["docNumber"], doc_date, item["rowNumber"])
            if key in existing_keys:
                continue

            new_objects.append(
                DiscountCardTransaction(
                    code=code,
                    docguid=item.get("docGuid"),
                    doc_presentation=item.get("docPresentation", ""),
                    doc_number=item["docNumber"],
                    doc_date=doc_date,
                    opening_balance=item.get("openingBalance", 0),
                    income=item.get("income", 0),
                    expense=item.get("expense", 0),
                    closing_balance=item.get("closingBalance", 0),
                    row_number=item["rowNumber"],
                )
            )

        # 3) Hammasini BITTA so'rov bilan yozamiz
        if new_objects:
            DiscountCardTransaction.objects.bulk_create(
                new_objects,
                batch_size=500,
                ignore_conflicts=True,  # unique constraint bo'yicha qo'shimcha xavfsizlik
            )

    print(
        f"Report {'yaratildi' if created else 'yangilandi'}: {code}. "
        f"Jami: {len(items)} ta, yangi qo'shildi: {len(new_objects)} ta"
    )
    return code


if __name__ == "__main__":
    sync_card_transactions(code="7802139070649")