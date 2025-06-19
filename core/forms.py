from django import forms
from django.contrib.auth.models import User
from .models import Driver


class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']


class DriverRegisterForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['phone_number', 'vehicle_number']
