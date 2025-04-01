from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.middleware.csrf import get_token
from .serialezers import ProductsSerializer
from rest_framework import generics
from .models import Products
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
import json
import secrets



def get_all_products(request):
    all_products = Products.objects.all()

    serialized_products = ProductsSerializer(all_products, many=True, context={'request': request})

    return JsonResponse(serialized_products.data, safe=False)

def get_product_by_id(request, id):
    product = Products.objects.filter(pk=id).first()

    serializer = ProductsSerializer(product, context={'request': request})

    return JsonResponse(serializer.data, safe=False)

@csrf_exempt
def send_test_mail(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))

            token = secrets.token_urlsafe(16)
            
            cache.set(data['email'], token, timeout=3600)
            
            verification_link = f"http://localhost:3000/verify/email/{data['email']}/{token}/"
            
            send_mail(
                'Test Email',
                f"Добрий день {data['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
                settings.EMAIL_HOST_USER,
                [data['email']],
                fail_silently=False,
            )
        except:
            return JsonResponse({'error': 'Failed to send email'}, status=500)
    return HttpResponse('ok')

def verify_email(request, email, token):
    stored_token = cache.get(email)  # Проверяем токен в Redis
    if stored_token and stored_token == token:
        cache.delete(email)  # Удаляем токен после проверки
        return JsonResponse({"Email подтверждён!"})
    
    return JsonResponse({"Неверный токен"}, status=400)

def get_csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})