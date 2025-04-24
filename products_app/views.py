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

def get_all_products(request):
    try:
        all_products = Products.objects.all()
        serializer = ProductsSerializer(all_products, many=True, context={'request': request})
        return JsonResponse({
            "status":"succes",
            'data':serializer.data
        }, safe=False)
    except:
        return JsonResponse({
            'status':'error',
            'message':'loading products error'
        }, safe=False)
        

def get_product_by_id(request, id):
    try:
        product = Products.objects.filter(pk=id).first()
        serializer = ProductsSerializer(product, context={'request': request})
        return JsonResponse({
            "status":"succes",
            'data':serializer.data
        }, safe=False)
    except:
        return JsonResponse({
            'status':'error',
            'message':'loading product error'
        }, safe=False)

# Обход csrf проверки
@csrf_exempt
def send_order(request):
    try:
        # Получает запрос с данными о заказе и форматируем его в json строку
        data = json.loads(request.body.decode('utf-8'))
        
        # Создаем токен заказа
        token = secrets.token_urlsafe(16)
        
        # Разбиваем данные с запроса на переменные 
        userData = data['userData']
        productsInCart = data['productsInCart']
        
        # Создаем список всех айдишников с запроса
        product_ids = [item['id'] for item in productsInCart]
        # Создаем список обьектов всех продуктов с запроса в стиле: {id:count}
        id_to_count = {item['id']: item['count'] for item in productsInCart}

        # Получаем все продукты с базы данных по айдишникам с запроса
        products = Products.objects.filter(id__in=product_ids)

        # Создаем список где будут хранится все продукты
        serialized_products = []
        # Перебираем массив продуктов и добавляем к нему количество
        for product in products:
            # Переделываем queryset продукт в обыект
            serialized = ProductsSerializer(product).data
            # Добавляем количество продукта
            serialized['count'] = id_to_count.get(product.id, 0)
            # Записуем его в список всех продуктов 
            serialized_products.append(serialized)

        # Создаем строку где будут все продукты для записи их в сообщение
        product_details = ""
        for product in serialized_products:
            product_details += f"Продукт: {product['name']}\nКількість: {product['count']}\n\n"

        # Создаем сообщение которое увидит кондитер
        message = (
            f"Ім'я: {userData['name']} {userData['surname']}\n"
            f"Номер телефону: {userData['phone']}\n"
            f"Пошта: {userData['email']}\n"
            f"Тип доставки: {userData['deliveryMethod']}\n"
            f"Сумма заказу: {data['totalSum']}\n"
            f"Продукти в замовленні:\n{product_details}"
        )

        # Добавляем сообщение в userData чтоб оттуда взяты данные о пользователе
        userData['message'] = message

        # Создаем ссылку для проверки почты
        verification_link = f"http://localhost:8000/verify/email/{userData['email']}/{token}/"

        # Создаем обьект который мы будем кешироваты в котором будет все нужные данные для проверки почти и отправки писыма заказа
        orderInfo = {
            "userData": userData,
            "token": token,
            "title": "Заказ",
            'totalSum': data['totalSum'],
            # 'pay': 'yes',
        }

        # Сохраняем заказ в Redis через Upstash REST API
        upstash_redis_set(token, orderInfo)

        # Отправляем писамо клиенту на подтверждение почты
        send_mail(
            'Підтверження пошти',
            f"Добрий день {userData['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
            settings.EMAIL_HOST_USER,
            [userData['email']],
            fail_silently=False,
        )

        # Отправляем ответ если все удалосы
        return JsonResponse({
            "status": "ok",
            'data': None
        })
    except:
        return JsonResponse({
            'status':'error',
            'message':'Не вдалося Зробити заказ'
        }, safe=False)

@csrf_exempt
def send_self_order(request):
    try:
        # Получает запрос с данными о заказе и форматируем его в json строку
        data = json.loads(request.body.decode('utf-8'))

        # Создаем токен заказа
        token = secrets.token_urlsafe(16)

        # Создаем сообщение которое увидит кондитер
        message = (
            f"Ім'я: {data['name']} {data['surname']}\n"
            f"Номер телефону: {data['phone']}\n"
            f"Пошта: {data['email']}\n"
            f"Заказ:\n{data['describeOrder']}"
        )

        # Добавляем сообщение к userData 
        # (Для етого не сделана отделыная переменная как в views send_order потому-что мы там отправляем userData и список продуктов которые заказа пользователь а тут мы отпраляем только userData)
        data['message'] = message

        # Создаем обьект который мы будем кешироваты в котором будет все нужные данные для проверки почти и отправки писыма заказа
        order_info = {
            'token': token,
            "userData": data,
            'title': "Особистий заказ",
        }

        # Создаем ссылку для проверки почты
        verification_link = f"http://localhost:8000/verify/email/{data['email']}/{token}/"

        # Сохраняем заказ в Redis через Upstash REST API
        upstash_redis_set(token, order_info)

        # Отправляем писамо клиенту на подтверждение почты
        send_mail(
            'Підтверження пошти',
            f"Добрий день {data['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
            settings.EMAIL_HOST_USER,
            [data['email']],
            fail_silently=False,
        )

        # Отправляем ответ если все удалосы
        return JsonResponse({
            "status": "ok",
            'data': None
        })
    except Exception as e:
        return JsonResponse({
            'status':'error',
            'message':'Не вдалося Зробити заказ'
        }, safe=False)

def verify_email(request, email, token):
    # Получаем кашированные данные по токену заказа
    data = upstash_redis_get(token)

    # Создаем проверку на наличие токена
    if not data or data['token'] != token:
        return JsonResponse({
            'status':'error',
            'message':'Невірний токен'
        }, safe=False)

    # Отправляем сообщение кондитеру о новом заказе
    send_mail(
        "Новий заказ",
        data['userData']['message'],
        settings.EMAIL_HOST_USER,
        ['likeemangames@gmail.com'],
        fail_silently=False
    )

    return JsonResponse({
        "status": "ok",
        'data': None
    })
