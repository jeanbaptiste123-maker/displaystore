from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Product, Profile


class SignUpForm(UserCreationForm):
    user_type = forms.ChoiceField(
        choices=Profile.USER_TYPE,
        widget=forms.RadioSelect,
        label="Register as",
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'user_type')


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'stock', 'image']
