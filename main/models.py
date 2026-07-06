import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import transaction, IntegrityError

class DiscountPercent(models.Model):
    percent = models.DecimalField(max_digits=2, decimal_places=0, default=1, verbose_name="Chegirma foizi")


class CustomUser(AbstractUser):
    """
    KSB AFM API dan keladigan diskont karta ma'lumotlariga mos custom user.
 
    - uid1c -> 1C tizimidagi GUID, unique, avtomatik generatsiya qilinadi
    - code  -> karta kodi, unique. Boshidagi 7 belgi (CODE_PREFIX) barcha
               userlarda bir xil, qolgan qismi avtomatik unique generatsiya qilinadi
    """
 
    CODE_PREFIX = "7802013"
    CODE_SUFFIX_LENGTH = 5  # 7 (prefix) + 5 (ketma-ket raqam) = 12 xonali asos, +1 checksum = 13
 
    uid1c = models.UUIDField(unique=True, editable=False, verbose_name="1C UID")
    code = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Karta kodi")
 
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Familiya")
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Ism")
    middle_name = models.CharField(max_length=150, blank=True, verbose_name="Otasining ismi")
    full_name = models.CharField(max_length=450, blank=True, verbose_name="To'liq F.I.O.")
    login_code = models.CharField(max_length=50, null=True, blank=True )
    discount_percent = models.ForeignKey(
        DiscountPercent,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="Chegirma foizi",
    )
 
    expiry_date = models.DateTimeField(null=True, blank=True, verbose_name="Amal qilish muddati")
    registration_date = models.DateTimeField(null=True, blank=True, verbose_name="Ro'yxatga olingan sana")
    birth_date = models.DateTimeField(null=True, blank=True, verbose_name="Tug'ilgan sana")
 
    is_card_active = models.BooleanField(default=True, verbose_name="Karta faol")
    registration = models.BooleanField(default=False, verbose_name="Registratsiya belgisi")
 
    address = models.CharField(max_length=500, blank=True, verbose_name="Manzil")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Telefon raqami")
 
    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["phone_number"]),
        ]


    def __str__(self):
        return f"{self.code} - {self.full_name}"
 
    @property
    def code_prefix(self):
        """Kodning boshidagi 7 ta belgisi (barcha userlarda umumiy bo'ladigan qism)."""
        return self.code[:7]
 
    @property
    def code_suffix(self):
        """Kodning individual (unique) qismi."""
        return self.code[7:]
 
    @staticmethod
    def _ean13_checksum(base_12_digits: str) -> str:
        """
        EAN-13 uchun tekshiruv (checksum) raqamini hisoblaydi.
        base_12_digits - 12 ta raqamdan iborat satr bo'lishi shart.
        """
        digits = [int(d) for d in base_12_digits]
        odd_sum = sum(digits[0::2])
        even_sum = sum(digits[1::2])
        total = odd_sum + even_sum * 3
        checksum = (10 - (total % 10)) % 10
        return str(checksum)
 
    @classmethod
    def _generate_code(cls):
        """
        CODE_PREFIX (7) + ketma-ket raqam (5) = 12 xonali asos,
        so'ng EAN-13 checksum qo'shilib, 13 xonali to'g'ri EAN-13 kod hosil bo'ladi.
 
        MIN_SEQUENCE - 1C'dan import qilingan haqiqiy kartalar orasidagi eng
        katta sequence qiymati (masalan data.json tahlili natijasida topilgan:
        7802013 prefiksidagi eng kattasi 90000). Bu qiymat pastki chegara
        sifatida ishlatiladi - shunda, hatto barcha 1C kartalari hali DB'ga
        to'liq import qilinmagan bo'lsa ham, yangi generatsiya qilingan kod
        ularning birortasi bilan to'qnashmaydi.
        """
        MIN_SEQUENCE = 90000
 
        last_user = (
            cls.objects
            .filter(code__startswith=cls.CODE_PREFIX)
            .order_by("-code")
            .first()
        )
 
        if last_user:
            last_suffix = last_user.code[len(cls.CODE_PREFIX):-1]
            current_max = int(last_suffix)
        else:
            current_max = 0
 
        next_number = max(current_max, MIN_SEQUENCE) + 1
 
        suffix = str(next_number).zfill(cls.CODE_SUFFIX_LENGTH)
        base_12 = f"{cls.CODE_PREFIX}{suffix}"
        checksum = cls._ean13_checksum(base_12)
        return f"{base_12}{checksum}"
 
    def save(self, *args, **kwargs):
        if not self.uid1c:
            self.uid1c = uuid.uuid4()
 
        if not self.discount_percent_id:
            last_discount = DiscountPercent.objects.order_by("id").last()
            if last_discount is None:
                last_discount = DiscountPercent.objects.create(percent=1)
            self.discount_percent = last_discount
 
        # Agar code hali generatsiya qilinmagan bo'lsa (yangi user),
        # race condition (bir vaqtda 2 ta so'rov bir xil kodni generatsiya
        # qilib qolishi) ehtimoliga qarshi retry mexanizmi bilan saqlaymiz.
        if not self.code:
            max_attempts = 5
            for attempt in range(max_attempts):
                self.code = self._generate_code()
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.code = None  # keyingi urinishda qayta generatsiya qilinsin
                    if attempt == max_attempts - 1:
                        raise
                    continue
 
        super().save(*args, **kwargs)
 


class DiscountCardReport(models.Model):
    uid1c = models.UUIDField(unique=True)
    code = models.CharField(max_length=50, db_index=True)
    full_name = models.CharField(max_length=255)
    discount_percent = models.DecimalField(max_digits=5,decimal_places=2,default=0)
    period_from = models.DateTimeField()
    period_to = models.DateTimeField()
    opening_balance = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    total_income = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    total_expense = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    closing_balance = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.code} - {self.full_name}"


class DiscountCardTransaction(models.Model):
    docguid = models.UUIDField(unique=True)
    code = models.ForeignKey(DiscountCardReport, on_delete=models.CASCADE, related_name="transactions")
    row_number = models.PositiveIntegerField()
    doc_presentation = models.CharField(max_length=500)
    doc_number = models.CharField(max_length=100,db_index=True)
    doc_date = models.DateTimeField()
    opening_balance = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    income = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    expense = models.DecimalField(max_digits=18,decimal_places=2,default=0)
    closing_balance = models.DecimalField(max_digits=18,decimal_places=2,default=0)


class EskizToken(models.Model):
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token
    

from io import BytesIO
import qrcode
from django.core.files.base import ContentFile



class QrCode(models.Model):
    uid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to="qrcodes/", blank=True, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    BASE_URL = "http://localhost:8000/api/v1/code/"

    @property
    def qr_url(self):
        return f"{self.BASE_URL}{self.uid}/"

    def generate_qr_image(self):
        """QR kod rasmini generatsiya qilib, ContentFile sifatida qaytaradi."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        filename = f"{self.uid}.png"
        return ContentFile(buffer.getvalue(), name=filename)

    def save(self, *args, **kwargs):
        # Yangi obyekt yaratilayotganda yoki rasm hali yo'q bo'lsa - generatsiya qilamiz
        is_new = self._state.adding

        # avval uid/id bo'lishi uchun bir marta saqlab olamiz (agar image hali yo'q bo'lsa)
        if is_new and not self.image:
            super().save(*args, **kwargs)
            self.image = self.generate_qr_image()
            # faqat image maydonini yangilaymiz, cheksiz recursiyaga tushmaslik uchun
            super().save(update_fields=["image"])
            return

        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.uid)
    


@receiver(post_delete, sender=QrCode)
def delete_qr_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
