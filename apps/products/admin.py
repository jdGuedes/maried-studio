from django.contrib import admin
from .models import Product, ProductAsset
admin.site.register([Product, ProductAsset])
