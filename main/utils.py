import re
from .models import CustomUser
import random
import requests
from .models import EskizToken
from django.utils import timezone
from datetime import timedelta
import base64
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from django.conf import settings

LOGIN = settings.API_1C_LOGIN
PASSWORD = settings.API_1C_PASSWD
SMS_EMAIL_API_KEY = settings.SMS_EMAIL_API_KEY
SMS_PASSWORD = settings.SMS_PASSWORD

def create_1c_user(user):
    """
    1C'ga user ma'lumotini yuborib, diskont karta yaratish/topish uchun.
    POST /hs/discountcards/register
    """
    try:
        response = requests.post(
            "http://93.170.11.10:8087/MainBase/hs/discount_api/register",
            json={
                "code": user.code,
                "lastName": user.last_name,
                "firstName": user.first_name,
                "middleName": user.middle_name,
                "fullName": user.full_name,
                "birthDate": str(user.birth_date) if user.birth_date else None,
                "phoneNumber": user.phone_number,
            },
            auth=(LOGIN, PASSWORD),   # <-- yetishmayotgan qism shu edi
            timeout=30,
        )
    except requests.RequestException as e:
        return {"success": False, "error": f"So'rov yuborishda xato: {e}"}

    # Javob bo'sh yoki JSON bo'lmasa - xom matnni qaytaramiz, json() chaqirib xato bermaymiz
    if not response.text:
        return {
            "success": False,
            "error": "1C bo'sh javob qaytardi",
            "status_code": response.status_code,
        }

    try:
        return response.json()
    except ValueError:
        return {
            "success": False,
            "error": "1C JSON bo'lmagan javob qaytardi",
            "status_code": response.status_code,
            "raw_response": response.text[:500],
        }

def get_eskiz_token():

    token  = EskizToken.objects.last()
    if token and timezone.now() - token.created_at < timedelta(hours=24):
        return token.token

    url = "https://notify.eskiz.uz/api/auth/login"
    payload = {
        "email": SMS_EMAIL_API_KEY,
        "password": SMS_PASSWORD
    }

    response = requests.post(url, data=payload)

    if response.status_code == 200:
        token = response.json().get("data", {}).get("token")
        data = response.json()

    if "data" in data and "token" in data["data"]:
        new_token = data["data"]["token"]
        EskizToken.objects.all().delete()  # eski tokenlarni o‘chirish
        EskizToken.objects.create(token=new_token)  # yangisini saqlash
        return new_token
    else:
        raise Exception(f"Eskiz token olishda xatolik: {data}")

def clean_phone_number(phone_number):
    """Telefon raqamini 998XXXXXXXXX formatiga o'tkazish"""
    phone_number = re.sub(r'\D', '', phone_number)

    if phone_number.startswith("998") and len(phone_number) == 12:
        return phone_number
    elif phone_number.startswith("9") and len(phone_number) == 9:
        return "998" + phone_number
    elif phone_number.startswith("0") and len(phone_number) == 10:
        return "998" + phone_number[1:]
    else:
        return None

def send_sms(phone_number, code):
    # phone_number = clean_phone_number(phone_number)
    """Eskiz orqali SMS yuborish"""
    token = get_eskiz_token()
    if not token:
        return {"error": "Eskiz API tokenini olishda xatolik!"}

    url = "https://notify.eskiz.uz/api/message/sms/send"

    headers = {"Authorization": f"Bearer {token}"}

    phone_number = phone_number.replace("+", "").replace(" ", "").strip()
    if not phone_number.startswith("998") or len(phone_number) != 12:
        return {"error": "Telefon raqami noto‘g‘ri formatda!"}
    payload = {
    "mobile_phone": phone_number,
    "message": f"Kodni hech kimga bermang! Akmal Farm mobil ilovasiga kirish uchun tasdiqlash kodi: {code}",
    "from": "4546",
    "callback_url": ""
    }

    response = requests.post(url, headers=headers, data=payload)
    # print("Eskizdan javob:", response.json())
    return response.json()

def random_number():
    while True:
        code = random.randint(10000, 99999)
        user = CustomUser.objects.filter(login_code=code).exists()
        if not user:
            return code

def generate_barcode_base64(code):
    ean = barcode.get('ean13', code, writer=ImageWriter())

    buffer = BytesIO()
    ean.write(buffer)

    return base64.b64encode(buffer.getvalue()).decode()