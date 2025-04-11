from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
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
import uuid
import requests



def get_all_products(request):
    all_products = Products.objects.all()

    serialized_products = ProductsSerializer(all_products, many=True, context={'request': request})

    return JsonResponse(serialized_products.data, safe=False)

def get_product_by_id(request, id):
    product = Products.objects.filter(pk=id).first()

    serializer = ProductsSerializer(product, context={'request': request})

    return JsonResponse(serializer.data, safe=False)

@csrf_exempt
def send_order(request):
    data = json.loads(request.body.decode('utf-8'))
    userData = data['userData']
    totalSum = data['totalSum']

    token = secrets.token_urlsafe(16)
    order_id = str(uuid.uuid4())
    payment_url = f"http://localhost:3000/fake-payment/{order_id}/"  # ← фейковая ссылка

    verification_link = f"http://localhost:8000/verify/email/{userData['email']}/{token}/"

    userData['message'] = f"Ім'я: {userData['name']}\nEmail: {userData['email']}\nСума: {totalSum}"

    order_info = {
        "token": token,
        "userData": userData,
        "order_id": order_id,
        "payment_url": payment_url,
    }

    cache.set(token, order_info, timeout=3600)

    send_mail(
        'Підтвердження пошти',
        f"Привіт, підтвердіть пошту за посиланням: {verification_link}",
        settings.EMAIL_HOST_USER,
        [userData['email']],
        fail_silently=False
    )

    return JsonResponse({"status": "ok"})


@csrf_exempt
def send_self_order(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        
        print(1)
        
        token = secrets.token_urlsafe(16)
        
        # cache.set(data['email'], token, timeout=3600)
        
        print(data)
        
        message = (
            f"Ім'я: {data['name']} {data['surname']}\n"
            f"Номер телефону: {data['phone']}\n"
            f"Пошта: {data['email']}\n"
            f"Заказ:\n{data['describeOrder']}"
        )
        
        order_info = {
            'token':token,
            "data":data,
            'message':message,
            'title':'   '
        }

        # print(tokenbebra)        

        verification_link = f"http://localhost:8000/verify/email/{data['email']}/{token}/"
        
        cache.set(token, order_info)
        
        
        # send_mail(
        #     'Підтверження пошти',
        #     f"Добрий день {data['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
        #     settings.EMAIL_HOST_USER,
        #     [data['email']],
        #     fail_silently=False,
        # )
        
        
        # send_mail(
        #     'Особистий заказ',
        #     message,
        #     settings.EMAIL_HOST_USER,
        #     ['likeemangames@gmail.com'],
        #     fail_silently=False,
        # )

        return HttpResponse('ok')
    except:
        return JsonResponse({'error': 'Failed to send email'}, status=500)

def verify_email(request, email, token):
    data = cache.get(token)

    if not data or data['token'] != token:
        return JsonResponse({"error": "Невірний токен"}, status=400)

    # отправляем данные админу
    send_mail(
        "Новий заказ",
        data['userData']['message'],
        settings.EMAIL_HOST_USER,
        ['likeemangames@gmail.com'],
        fail_silently=False
    )

    cache.delete(token)

    # редирект на ссылку оплаты
    return redirect(data['payment_url'])

def get_csrf(request):
    token = get_token(request)
    response = JsonResponse({"csrfToken": token} )
    response.set_cookie('csrf_token', token)
    return JsonResponse({"csrfToken": get_token(request)} )