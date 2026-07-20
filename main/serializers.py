from .models import Category, CustomUser , DiscountCardReport , DiscountCardTransaction, QrCode , GlavniImage  
from rest_framework import serializers

class DiscountCardTransaction1Serializer(serializers.ModelField):
    class Meta:
        model = DiscountCardTransaction
        fields = "__all__"


class DiscountCardReportSerializer1(serializers.ModelSerializer):
    # transactions = serializers.SerializerMethodField()
    class Meta:
        model = DiscountCardReport
        fields = "__all__"

class DiscountCardReportSerializer(serializers.ModelSerializer):
    transactions = serializers.SerializerMethodField()
    class Meta:
        model = DiscountCardReport
        fields = "__all__"

    def get_transactions(self, obj):
        transactions = obj.transactions.all()
        return DiscountCardTransactionSerializer(transactions, many=True).data

class DiscountCardTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCardTransaction
        fields = "__all__"



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'uid1c','code', 'first_name', 'last_name',  'phone_number', 'is_active','date_joined']

class QrCodeSerializer(serializers.ModelSerializer):
    # qr_url = serializers.ReadOnlyField()
    class Meta:
        model = QrCode
        fields = ['code' , 'image']
        read_only_fields = ["image", 'code']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
    
class GlavniySerializer(serializers.ModelSerializer):
    class Meta:
        model = GlavniImage
        fields = ['id', 'image']