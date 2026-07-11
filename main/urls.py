from django.urls import path
from .views import *
urlpatterns = [
    path('refresh-translation/', TranslationsApiView.as_view()),
    path('register/', api_user_register),
    path('register/phone/', api_user_register_phone),
    path('login/', api_login),
    path('send-sms/', api_send_sms),
    path('user-info/', api_get_user_info),
    # path('sync-card-transactions/', sync_card_transactions),
    path('qr-code/', QrCodeApiView.as_view()),
    path('code/<str:uid>/', get_code),
    path('refresh/', refresh),
    path('balance/', user_balance),
    path('translation/', api_translation)
]