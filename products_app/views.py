from django.http import JsonResponse
from django.shortcuts import render

from .serialezers import ProductsSerializer
from rest_framework import generics
from .models import Products

# Create your views here.




def get_all_products(request):
    all_products = Products.objects.all()
    
    serialized_products = ProductsSerializer(all_products, many=True)
    
    return JsonResponse(serialized_products.data, safe=False)