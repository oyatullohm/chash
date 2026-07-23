import os
import sys
import django

# Django settings-ni sozlash (BUNI ENGINE BOSHIDA QO'SHING)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Admin.settings')  # your_project o'rniga loyiha nomi
django.setup()

# Endi importlar
import json
import re
import requests
from datetime import datetime
from decimal import Decimal
from requests.auth import HTTPBasicAuth
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.contrib.auth.hashers import make_password

# Model importlari (django.setup() dan KEYIN)
from main.models import CustomUser, DiscountCardReport, DiscountCardTransaction

# ... qolgan kod ...
# 1C API sozlamalari
BASE_URL = "http://93.170.11.10:8087/MainBase/hs/discount_api/transactions"
LOGIN = "1"
PASSWORD = "1"

import json
import re
import requests
import os
import sys
import django


CODE_PATTERN = re.compile(r"^\d{13}$")


# ================ YORDAMCHI FUNKSIYALAR ================

def generate_username(code, phone_number=""):
    """
    Username generatsiya qilish:
    1. Agar telefon raqam bo'lsa - uni ishlatamiz
    2. Bo'lmasa - code ni ishlatamiz
    3. Agar mavjud bo'lsa - oxiriga raqam qo'shamiz
    """
    base_username = phone_number if phone_number else code
    
    # Agar username mavjud bo'lmasa - qaytaramiz
    if not CustomUser.objects.filter(username=base_username).exists():
        return base_username
    
    # Agar mavjud bo'lsa - oxiriga raqam qo'shamiz
    counter = 1
    while True:
        new_username = f"{base_username}_{counter}"
        if not CustomUser.objects.filter(username=new_username).exists():
            return new_username
        counter += 1


def parse_dt(value: str):
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


# ================ 1C API ================

class CardNotFoundError(Exception):
    pass


class Card1CApiError(Exception):
    pass


def fetch_card_transactions(card_code: str, date_from: str = None, date_to: str = None) -> dict:
    params = {"code": card_code}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    
    try:
        response = requests.get(
            BASE_URL,
            params=params,
            auth=HTTPBasicAuth(LOGIN, PASSWORD),
            timeout=30
        )
    except requests.RequestException as e:
        raise Card1CApiError(f"1C serverga ulanishda xato: {e}")
    
    if response.status_code == 400:
        raise CardNotFoundError(f"Karta topilmadi: {response.text}")
    
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise Card1CApiError(f"1C API xatosi: {response.text[:300]}")
    
    return response.json()


# ================ TRANZAKSIYALARNI SYNC QILISH ================

def sync_user_transactions(card_code: str, date_from: str = None, date_to: str = None):
    data = fetch_card_transactions(card_code, date_from, date_to)
    
    with transaction.atomic():
        report, created = DiscountCardReport.objects.update_or_create(
            code=data["code"],
            defaults={
                "uid1c": data["uid1c"],
                "full_name": data.get("fullName", ""),
                "discount_percent": data.get("discountPercent", 0),
                "period_from": parse_iso_datetime(data.get("periodFrom")),
                "period_to": parse_iso_datetime(data.get("periodTo")),
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
            doc_date = parse_iso_datetime(item.get("docDate"))
            key = (item.get("docNumber"), doc_date, item.get("rowNumber"))
            if key in existing_keys:
                continue
            
            new_objects.append(
                DiscountCardTransaction(
                    code=report,
                    docguid=item.get("docGuid"),
                    doc_presentation=item.get("docPresentation", ""),
                    doc_number=item.get("docNumber"),
                    doc_date=doc_date,
                    opening_balance=item.get("openingBalance", 0),
                    income=item.get("income", 0),
                    expense=item.get("expense", 0),
                    closing_balance=item.get("closingBalance", 0),
                    row_number=item.get("rowNumber"),
                )
            )
        
        if new_objects:
            DiscountCardTransaction.objects.bulk_create(
                new_objects,
                batch_size=500,
                ignore_conflicts=True,
            )
    
    return report, created, len(new_objects)


# ================ ASOSIY IMPORT FUNKSIYASI ================

def import_users_and_transactions(json_path="data.json", max_users=None, no_transactions=False):
    print("=" * 60)
    print("📊 USER VA TRANZAKSIYA IMPORT BOSHLANDI")
    print("=" * 60)
    
    # JSON ni o'qish
    print(f"\n📌 {json_path} fayli o'qilmoqda...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, dict) and "data" in data:
        cards = data["data"]
    else:
        cards = data
    
    total = len(cards)
    if max_users:
        cards = cards[:max_users]
        total = len(cards)
    
    print(f"   📦 Jami: {total} ta karta import qilinadi")
    
    # Userlarni yaratish
    print("\n📌 Userlar yaratilmoqda...")
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    users_list = []
    
    for i, item in enumerate(cards, 1):
        try:
            code = (item.get("code") or "").strip()
            uid1c = item.get("uid1c")
            
            if not CODE_PATTERN.match(code):
                skipped_count += 1
                print(f"   ⚠️ [{i}/{total}] O'tkazib yuborildi (code noto'g'ri): {code!r}")
                continue
            
            # Telefon raqamini tozalash
            phone_number = (item.get("phoneNumber") or "").strip()
            if phone_number:
                phone_number = ''.join(filter(str.isdigit, phone_number))
                if len(phone_number) == 9:
                    phone_number = f"+998{phone_number}"
                elif len(phone_number) == 12:
                    phone_number = f"+{phone_number}"
            
            # ✅ USERNAME GENERATSIYA QILISH
            username = generate_username(code, phone_number)
            
            discount_percent_value = item.get("discountPercent", 0) or 0
            
            # Userni topish yoki yaratish
            user, created = CustomUser.objects.get_or_create(
                uid1c=uid1c,
                defaults={
                    'code': code,
                    'username': username,  # ✅ Username qo'shildi
                    'last_name': item.get("lastName", ""),
                    'first_name': item.get("firstName", ""),
                    'middle_name': item.get("middleName", ""),
                    'full_name': item.get("fullName", ""),
                    'discount_percent': discount_percent_value,
                    'expiry_date': parse_dt(item.get("expiryDate")),
                    'registration_date': parse_dt(item.get("registrationDate")),
                    'birth_date': parse_dt(item.get("birthDate")),
                    'is_card_active': item.get("isActive", False),
                    'registration': item.get("registration", False),
                    'address': item.get("address", ""),
                    'phone_number': phone_number,
                    'password': make_password(f"password_{code}")
                }
            )
            
            if not created:
                # Mavjud userni yangilash
                user.code = code
                user.username = username  # ✅ Username yangilandi
                user.last_name = item.get("lastName", "")
                user.first_name = item.get("firstName", "")
                user.middle_name = item.get("middleName", "")
                user.full_name = item.get("fullName", "")
                user.discount_percent = discount_percent_value
                user.expiry_date = parse_dt(item.get("expiryDate"))
                user.registration_date = parse_dt(item.get("registrationDate"))
                user.birth_date = parse_dt(item.get("birthDate"))
                user.is_card_active = item.get("isActive", False)
                user.registration = item.get("registration", False)
                user.address = item.get("address", "")
                user.phone_number = phone_number
                user.save()
                updated_count += 1
                print(f"   🔄 [{i}/{total}] Yangilandi: {code} - {user.username}")
            else:
                created_count += 1
                print(f"   ✅ [{i}/{total}] Yaratildi: {code} - {user.username}")
            
            users_list.append(user)
            
        except Exception as e:
            error_count += 1
            print(f"   ❌ [{i}/{total}] Xatolik: {str(e)}")
    
    print(f"\n   ✅ Yaratilgan: {created_count}, Yangilangan: {updated_count}")
    print(f"   ⏭️  O'tkazib yuborilgan: {skipped_count}, ❌ Xatolik: {error_count}")
    
    # Tranzaksiyalarni yuklash
    if not no_transactions and users_list:
        print("\n📌 Tranzaksiyalar yuklanmoqda...")
        trx_success = 0
        trx_errors = 0
        trx_not_found = 0
        total_transactions = 0
        
        for i, user in enumerate(users_list, 1):
            try:
                print(f"   [{i}/{len(users_list)}] {user.code}...", end=" ")
                
                try:
                    report, created, trx_count = sync_user_transactions(user.code)
                    total_transactions += trx_count
                    trx_success += 1
                    print(f"✅ {trx_count} ta tranzaksiya")
                except CardNotFoundError:
                    trx_not_found += 1
                    print("⚠️  Karta topilmadi")
                except Card1CApiError as e:
                    trx_errors += 1
                    print(f"❌ API xatosi: {str(e)[:50]}")
                    
            except Exception as e:
                trx_errors += 1
                print(f"❌ Xatolik: {str(e)[:50]}")
        
        print(f"\n   ✅ Yuklangan: {trx_success}")
        print(f"   ⚠️  Topilmadi: {trx_not_found}")
        print(f"   ❌ Xatolik: {trx_errors}")
        print(f"   📦 Jami tranzaksiyalar: {total_transactions}")
    
    print("\n" + "=" * 60)
    print("📊 IMPORT TUGADI!")
    print(f"   👤 Userlar: Yaratilgan={created_count}, Yangilangan={updated_count}")
    print(f"   ⏭️  O'tkazib yuborilgan: {skipped_count}")
    print(f"   ❌ Xatolik: {error_count}")
    print("=" * 60)


# ================ ASOSIY QISM ================

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    max_users = int(sys.argv[2]) if len(sys.argv) > 2 else None
    no_transactions = "--no-transactions" in sys.argv
    
    import_users_and_transactions(
        json_path=json_file,
        max_users=max_users,
        no_transactions=no_transactions
    )