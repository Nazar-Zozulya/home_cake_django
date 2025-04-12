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
        
    # Генерация уникального токена и order_id
    token = secrets.token_urlsafe(16)
    order_id = str(uuid.uuid4())  # Генерируем уникальный order_id
    
    userData = data['userData']
    productsInCart = data['productsInCart']
    
    product_ids = [item['id'] for item in productsInCart]
    id_to_count = {item['id']: item['count'] for item in productsInCart}
    
    order_id = str(uuid.uuid4())
    payment_url = f"http://localhost:3000/fake-payment/{order_id}/"  # ← фейковая ссылка

    products = Products.objects.filter(id__in=product_ids)
    
    serialized_products = []
    for product in products:
        serialized = ProductsSerializer(product).data
        serialized['count'] = id_to_count.get(product.id, 0)
        serialized_products.append(serialized)
    
    print(serialized_products)
    
    product_details = ""
    for product in serialized_products:
        product_details += f"Продукт: {product['name']}\nКількість: {product['count']}\n\n"
    
    message = (
        f"Ім'я: {userData['name']} {userData['surname']}\n"
        f"Номер телефону: {userData['phone']}\n"
        f"Пошта: {userData['email']}\n"
        f"Тип доставки: {userData['deliveryMethod']}\n"
        f"{f'Адреса: {userData['adress']}\nДата: {userData['data']}\nЧас: {userData['time']}\n' if userData['deliveryMethod'] == 'Доставка' else ''}"
        f"Сумма заказу: {data['totalSum']}\n"
        f"Продукти в замовленні:\n{product_details}"
    )
    
    userData['message'] = message
    
    verification_link = f"http://localhost:8000/verify/email/{userData['email']}/{token}/"
    
    orderInfo = {
        "userData": userData,
        "token": token,
        "title": "Заказ",
        'totalSum':data['totalSum'],
        'pay':'yes',
    }
    
    cache.set(token, orderInfo, timeout=3600)  # Сохраняем заказ в кеш
    
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
        
        print(1)
        
        token = secrets.token_urlsafe(16)        
        print(data)
        
        message = (
            f"Ім'я: {data['name']} {data['surname']}\n"
            f"Номер телефону: {data['phone']}\n"
            f"Пошта: {data['email']}\n"
            f"Заказ:\n{data['describeOrder']}"
        )
        
        data['message'] = message
        
        order_info = {
            'token':token,
            "userData":data,
            # 'message':message,
            'title':"Особистий заказ",
        }    

        verification_link = f"http://localhost:8000/verify/email/{data['email']}/{token}/"
        
        cache.set(token, order_info, timeout=3600)
        
        
        send_mail(
            'Підтверження пошти',
            f"Добрий день {data['name']} Підтвердіть свою пошту по цьому посиланню: {verification_link}",
            settings.EMAIL_HOST_USER,
            [data['email']],
            fail_silently=False,
        )

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
    
    
    
    if(data.get('pay', False) != False):
        monobank_json = {
            "amount": int(f"{data['totalSum']}00"),
            "ccy": 980,
            "merchantPaymInfo": {
                "reference": "84d0070ee4e44667b31371d8f8813947",
                "destination": "Покупка щастя",
                "comment": "Покупка щастя",
                "customerEmails": [],
            }
        }
        api_token = "ug89PDMsFgQ5AWMpyubBNo5qyPkwiXS6EJ-_hqSyu7zI"
        
        response = requests.post('https://api.monobank.ua/api/merchant/invoice/create', json=monobank_json, headers={'X-Token': api_token}).json()

        # page_url = response['pageUrl']
        
        # return JsonResponse(page_url, safe=False)
        return redirect(response['pageUrl'])
    else:
        return JsonResponse(data)
    
def get_csrf(request):
    token = get_token(request)
    response = JsonResponse({"csrfToken": token} )
    response.set_cookie('csrf_token', token)
    return JsonResponse({"csrfToken": get_token(request)} )