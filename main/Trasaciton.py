from datetime import datetime

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import DiscountCardReport, DiscountCardTransaction

BASE_URL = "http://93.170.11.10:8087/MainBase/hs/discount_api/transactions"
LOGIN = settings.API_1C_LOGIN
PASSWORD = settings.API_1C_PASSWD


class CardNotFoundError(Exception):
    """1C'da shu kod bilan karta topilmaganda ko'tariladi."""
    pass


class Card1CApiError(Exception):
    """1C API bilan boshqa turdagi xato (500, timeout va h.k.) yuz berganda ko'tariladi."""
    pass


def parse_iso_datetime(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if timezone.is_naive(dt):
        try:
            dt = timezone.make_aware(dt)
        except Exception:
            pass
    return dt


def fetch_card_transactions(card_code: str, date_from: str = None, date_to: str = None) -> dict:
    params = {"code": card_code}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to

    try:
        response = requests.get(BASE_URL, params=params, auth=(LOGIN, PASSWORD), timeout=30)
    except requests.RequestException as e:
        raise Card1CApiError(f"1C serverga ulanishda xato: {e}")

    if response.status_code == 400:
        # Hujjatga ko'ra: karta topilmasa yoki parametr xato bo'lsa 400 qaytadi,
        # javob tanasi oddiy matn (masalan "Дисконт карта топилмади")
        raise CardNotFoundError(
            f"Karta topilmadi yoki so'rov xato (code={card_code}): {response.text}"
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise Card1CApiError(f"1C API xatosi (status={response.status_code}): {response.text[:300]}")

    return response.json()


def sync_card_transactions(card_code: str, date_from: str = None, date_to: str = None):
    """
    - Report: bitta update_or_create
    - Transactions: mavjudlarini 1 SELECT bilan o'qib, faqat yangilarini bulk_create qiladi
    - Agar 1C'da karta topilmasa -> CardNotFoundError ko'tariladi (chaqiruvchi ushlab, mos javob qaytarishi kerak)
    """
    data = fetch_card_transactions(card_code, date_from, date_to)

    with transaction.atomic():
        report, created = DiscountCardReport.objects.update_or_create(
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

        existing_keys = set(
            DiscountCardTransaction.objects
            .filter(code=report)
            .values_list("doc_number", "doc_date", "row_number")
        )

        new_objects = []
        for item in items:
            doc_date = parse_iso_datetime(item["docDate"])
            key = (item["docNumber"], doc_date, item["rowNumber"])
            if key in existing_keys:
                continue

            new_objects.append(
                DiscountCardTransaction(
                    code=report,
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

        if new_objects:
            DiscountCardTransaction.objects.bulk_create(
                new_objects,
                batch_size=500,
                ignore_conflicts=True,
            )

    return report