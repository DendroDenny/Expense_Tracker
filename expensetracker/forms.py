from django import forms
from django.contrib.auth import get_user_model

from .models import Expense, MonthlyBudget, Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name')


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('image',)


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ('amount', 'category', 'date', 'note')
        widgets = {
            'amount': forms.NumberInput(attrs={
                'min': '0.01',
                'step': '0.01',
                'placeholder': 'e.g. 10,000',
            }),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.TextInput(attrs={
                'placeholder': 'e.g. Lunch, taxi ride, etc.',
                'maxlength': '200',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Enter an amount greater than zero.')
        return amount


class MonthlyBudgetForm(forms.ModelForm):
    class Meta:
        model = MonthlyBudget
        fields = ('amount',)
        widgets = {
            'amount': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount < 0:
            raise forms.ValidationError('The monthly budget cannot be negative.')
        return amount
