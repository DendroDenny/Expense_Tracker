from django.contrib import admin

from .models import Expense, MonthlyBudget, Profile


admin.site.register((Expense, MonthlyBudget, Profile))
