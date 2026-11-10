from django import forms
from django.contrib.auth import get_user_model

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name')


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('image',)
