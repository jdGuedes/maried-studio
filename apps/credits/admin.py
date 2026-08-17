from django.contrib import admin
from .models import CreditTransaction, CreditWallet
admin.site.register([CreditWallet, CreditTransaction])
