
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from .Trasaciton import sync_card_transactions
from rest_framework.response import Response
from rest_framework.views import APIView
from .tasks import my_background_task
from django.http import JsonResponse
from django.core.cache import cache
from django.db import transaction
from rest_framework import status
from .serializers import *
from .utils import *

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_get_user_info(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def api_send_sms(request):
    if request.method == 'POST':
        phone = request.data.get('phone')
        try:
            user = CustomUser.objects.get(phone_number=phone)
        except:
            return Response({'success':False,'message':'User not found' })
        otp = random_number()
        user.login_code = otp
        user.save()
        response = send_sms(user.phone_number, otp)
        if "error" in response:
            return Response({'success':False,'message':response['error'] })
        return Response({'success':True,'message':'SMS yuborildi','otp':otp, 'response':response})

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def api_login(request):
    data = request.data
    code = data.get('code')
    user = CustomUser.objects.get(login_code=code)
    if user:
        refresh = RefreshToken.for_user(user)
        user.login_code = random_number()
        user.save()
        return JsonResponse({
            "message": "Login successful.",
            'success': True,
            'token': str(refresh.access_token),
            'refresh': str(refresh),
        })
    
    return JsonResponse({"message": "Login failed.", 'success': False}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def api_user_register(request):
    data = request.data
    last_name = data.get('last_name', '')
    first_name = data.get('first_name', '')
    # address = data.get('address', '')
    phone_number = data.get('phone', '')
    username = phone_number
    login_code = random_number()
    
    if CustomUser.objects.filter(username=username).exists():
        return JsonResponse({"message": "Username already exists.", 'success': False}, status=status.HTTP_400_BAD_REQUEST)
    user = CustomUser.objects.create_user(
        username=username,
        phone_number=phone_number,
        last_name=last_name,
        first_name=first_name,
        # address=address,
        # login_code=login_code
    )
    if user:
        otp = random_number()
        user.login_code = otp
        user.save()
        result = create_1c_user(user) 
        response = send_sms(user.phone_number, otp)
        if "error" in response:
            return Response({'success':False,'message':response['error'] })
        return Response({'success':True,'message':'SMS yuborildi','otp':otp, 'user_id': user.code, 'result':result})
    return JsonResponse({"message": "Registration failed.", 'success': False,}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def api_user_register_phone(request):

    data = request.data
    phone = data.get('phone')
    code = data.get('code')
    try:
        user = CustomUser.objects.get(code=code)
    except CustomUser.DoesNotExist:
        return Response({'success': False, 'message': 'User not found'})
    otp = random_number()
    user.phone_number = phone
    user.login_code = otp
    user.save()
    response = send_sms(user.phone_number, otp)
    if "error" in response:
        return Response({'success': False, 'message': response['error']})
    return Response({'success': True, 'message': 'SMS yuborildi', 'otp': otp, 'user_id': user.code})

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_balance(request):
    key = f"user_active:{request.user.id}"

    if not cache.get(key):
        cache.set(key, True, timeout=60 * 60 * 24)  # 1 kun
        my_background_task.delay(request.user.id)
        logger.info(
        f"[{timezone.now()}] Celery task queuega yuborildi. "
        f"user_id={request.user.id}"
    )
    else:
        logger.info(
        f"[{timezone.now()}] Celery task queuega yuborilmadi. "
        f"user_id={request.user.id}"
    )
    try:
        # code = request.user.code
        code = "7802139070649"
        balance = DiscountCardReport.objects.get(code=code)
    except DiscountCardReport.DoesNotExist:
        return Response({'success': False, 'message': 'Balance not found'}, status=status.HTTP_404_NOT_FOUND)
    balance_data = DiscountCardReportSerializer1(balance).data
    return Response({'success': True, 'balance':balance_data })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_translation(request):
    key = f"user_active:{request.user.id}"

    if not cache.get(key):
        cache.set(key, True, timeout=60 * 60 * 24)  # 1 kun
        my_background_task.delay(request.user.id)
    try:
        # code = request.user.code
        code = "7802139070649"
        balance = DiscountCardReport.objects.get(code=code)
    except DiscountCardReport.DoesNotExist:
        return Response({'success': False, 'message': 'Balance not found'}, status=status.HTTP_404_NOT_FOUND)
    balance_data = DiscountCardReportSerializer(balance).data
    return Response({'success': True, 'balance':balance_data })

    

class TranslationsApiView(APIView):
    def get(self, request):
        code = request.user.code
        sync_card_transactions(code=code)
        return Response({"success": True,})



class QrCodeApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.user.code

        with transaction.atomic():
            QrCode.objects.filter(code=code).delete()   # eskisi bo'lsa o'chiriladi (signal fayl ham o'chiradi)
            qr_code = QrCode.objects.create(code=code)   # har doim yangi yaratiladi

        return Response(QrCodeSerializer(qr_code, context={'request': request}).data)

@api_view(['GET'])
def get_code(request, uid):
    qr_code = QrCode.objects.filter(uid=uid, is_active=True).first()
    if qr_code:
        code = qr_code.code
        qr_code.delete()
        return Response({'success':True, 'code':code, "barcode": generate_barcode_base64(code)})
    return Response({"success": False, "message": "QR code not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def refresh(request):
    refresh_token = request.data.get('refresh')
    if refresh_token is None:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        return Response({'access': access_token}, status=status.HTTP_200_OK)
    except:
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

