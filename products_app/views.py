import json
import secrets
import requests
import os
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from dotenv import load_dotenv
from .serializers import ProductsSerializer
from .models import Products

# Загружаем переменные из .env
load_dotenv()

# Получаем URL и токен Upstash REST API из переменных окружения
UPSTASH_REST_URL = os.getenv("UPSTASH_REST_URL")
UPSTASH_REST_TOKEN = os.getenv("UPSTASH_REST_TOKEN")

# ===== Функции работы с Upstash Redis через REST API =====

def upstash_redis_set(key, value, timeout=3600):
    headers = {
        'Authorization': f'Bearer {UPSTASH_REST_TOKEN}',
        'Content-Type': 'application/json',
    }
    data = {
        "key": key,
        "value": json.dumps(value),
        "expire": timeout
    }
    response = requests.post(f"{UPSTASH_REST_URL}/set", headers=headers, json=data)
    return response.json()

def upstash_redis_get(key):
    headers = {
        'Authorization': f'Bearer {UPSTASH_REST_TOKEN}',
    }
    response = requests.get(f"{UPSTASH_REST_URL}/get/{key}", headers=headers)
    if response.status_code == 200:
        return json.loads(response.text).get("result")
    else:
        return None

def upstash_redis_delete(key):
    headers = {
        'Authorization': f'Bearer {UPSTASH_REST_TOKEN}',
    }
    response = requests.post(f"{UPSTASH_REST_URL}/del/{key}", headers=headers)
    return response.json()

# ===== Django Views =====

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

    # Генерация уникального токена
    token = secrets.token_urlsafe(16)

    userData = data['userData']
    productsInCart = data['productsInCart']

    product_ids = [item['id'] for item in productsInCart]
    id_to_count = {item['id']: item['count'] for item in productsInCart}

    products = Products.objects.filter(id__in=product_ids)

    serialized_products = []
    for product in products:
        serialized = ProductsSerializer(product).data
        serialized['count'] = id_to_count.get(product.id, 0)
        serialized_products.append(serialized)

    product_details = ""
    for product in serialized_products:
        product_details += f"Продукт: {product['name']}\nКількість: {product['count']}\n\n"

    message = (
        f"Ім'я: {userData['name']} {userData['surname']}\n"
        f"Номер телефону: {userData['phone']}\n"
        f"Пошта: {userData['email']}\n"
        f"Тип доставки: {userData['deliveryMethod']}\n"
        f"Сумма заказу: {data['totalSum']}\n"
        f"Продукти в замовленні:\n{product_details}"
    )

    userData['message'] = message

    verification_link = f"http://localhost:8000/verify/email/{userData['email']}/{token}/"

    orderInfo = {
        "userData": userData,
        "token": token,
        "title": "Заказ",
        'totalSum': data['totalSum'],
        'pay': 'yes',
    }

    # Сохраняем заказ в Redis через Upstash REST API
    upstash_redis_set(token, orderInfo)

    send_mail(
        'Підтверження пошти',
        f"Добрий день {userData['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
        settings.EMAIL_HOST_USER,
        [userData['email']],
        fail_silently=False,
    )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def send_self_order(request):
    try:
        data = json.loads(request.body.decode('utf-8'))

        token = secrets.token_urlsafe(16)

        message = (
            f"Ім'я: {data['name']} {data['surname']}\n"
            f"Номер телефону: {data['phone']}\n"
            f"Пошта: {data['email']}\n"
            f"Заказ:\n{data['describeOrder']}"
        )

        data['message'] = message

        order_info = {
            'token': token,
            "userData": data,
            'title': "Особистий заказ",
        }

        verification_link = f"http://localhost:8000/verify/email/{data['email']}/{token}/"

        # Сохраняем заказ в Redis через Upstash REST API
        upstash_redis_set(token, order_info)

        send_mail(
            'Підтверження пошти',
            f"Добрий день {data['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
            settings.EMAIL_HOST_USER,
            [data['email']],
            fail_silently=False,
        )

        return HttpResponse('ok')
    except Exception as e:
        return JsonResponse({'error': 'Failed to send email', 'details': str(e)}, status=500)

def verify_email(request, email, token):
    data = upstash_redis_get(token)

    if not data or data['token'] != token:
        return JsonResponse({"error": "Невірний токен"}, status=400)

    send_mail(
        "Новий заказ",
        data['userData']['message'],
        settings.EMAIL_HOST_USER,
        ['likeemangames@gmail.com'],
        fail_silently=False
    )

    return JsonResponse({"status": "ok"})
