from django.contrib import admin

# Register your models here.
from .models import * 

admin.site.register(DiscountPercent)
admin.site.register(DiscountCardReport)
admin.site.register(DiscountCardTransaction)
admin.site.register(QrCode)
admin.site.register(CustomUser)