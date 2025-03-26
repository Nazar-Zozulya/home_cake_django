from rest_framework import serializers
from .models import Products

class ProductsSerializer(serializers.ModelSerializer):
    full_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Products
        fields = '__all__'
        
    def get_full_image_url(self, obj):
        # Используем request для получения полного пути
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
        
        
    