from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.middleware.csrf import get_token
from .serialezers import ProductsSerializer
from rest_framework import generics
from .models import Products
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
# Create your views here.




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
        data = request.data()
        send_mail(
            'Test Email',
            f"{data}",
            'nazarcanva@gmail.com',
            ['likeemangames@gmail.com'],
            fail_silently=False,
        )
    
    return HttpResponse('ok')

def get_csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})