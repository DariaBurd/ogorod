from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import CustomerRegistrationForm, CustomerLoginForm
from .models import Product, Category



def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.first_name}!')
            return redirect('shop:catalog')  # ← Добавь 'shop:'
    else:
        form = CustomerRegistrationForm()

    return render(request, 'shop/register.html', {'form': form})

def catalog(request):
    """Страница каталога товаров"""
    categories = Category.objects.filter(is_active=True)[:3]
    featured_products = Product.objects.filter(
        is_active=True,
        quantity__gt=0
    )[:8]
    return render(request, 'shop/catalog.html', {
        'categories': categories,
        'products': featured_products  # ← ИСПРАВЬ НА featured_products!
    })

def user_login(request):
    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'С возвращением, {user.first_name}!')
                return redirect('shop:catalog')  # ← Добавь 'shop:'
    else:
        form = CustomerLoginForm()

    return render(request, 'shop/login.html', {'form': form})

from django.contrib.auth.decorators import login_required
from .models import ChatMessage

@login_required
def chat_room(request):
    messages = ChatMessage.objects.all()[:50]  # последние 50 сообщений
    return render(request, 'shop/chat_room.html', {'messages': messages})

@login_required
def send_message(request):
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            ChatMessage.objects.create(
                user=request.user,
                message=message_text
            )
    return redirect('shop:chat_room')