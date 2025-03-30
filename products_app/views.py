from django.http import JsonResponse
from django.shortcuts import render

from .serialezers import ProductsSerializer
from rest_framework import generics
from .models import Products
from django.core.mail import send_mail
# Create your views here.




def get_all_products(request):
    all_products = Products.objects.all()
        
    serialized_products = ProductsSerializer(all_products, many=True, context={'request': request})
    
    return JsonResponse(serialized_products.data, safe=False)

def get_product_by_id(request, id):
    product = Products.objects.filter(pk=id).first()
    
    serializer = ProductsSerializer(product, context={'request': request})
    
    return JsonResponse(serializer.data, safe=False)


def send_mail():
    
    send_mail(
        'Test Email',
        'This is a test email',
        'nazarcanva@gmail.com',
        ['likeemangames@gmail.com'],
        fail_silently=False,
    )