from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Customer


class CustomerRegistrationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '+7 (999) 123-45-67'})
    )
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'placeholder': 'Придумайте пароль'})
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={'placeholder': 'Повторите пароль'})
    )

    class Meta:
        model = Customer
        fields = ['email', 'phone', 'first_name', 'last_name', 'password1', 'password2']
        labels = {
            'email': 'Электронная почта',
            'phone': 'Номер телефона',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class CustomerLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Ваш email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Пароль'})
    )


from django import forms
from .models import ProductImport


class ProductImportForm(forms.ModelForm):
    class Meta:
        model = ProductImport
        fields = ['file']

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError('Поддерживаются только Excel файлы (.xlsx, .xls)')
        return file