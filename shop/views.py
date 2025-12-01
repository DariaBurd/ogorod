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


import pandas as pd
import requests
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import ProductImport
from .forms import ProductImportForm


def is_admin(user):
    return user.is_staff


@login_required
@user_passes_test(is_admin)
def product_import(request):
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            import_task = form.save(commit=False)
            import_task.created_by = request.user
            import_task.save()

            # Запускаем обработку
            process_excel_import(import_task)

            messages.success(request,
                             f'Импорт завершен! Успешно: {import_task.imported_count}, Ошибок: {import_task.error_count}')
            return redirect('shop:import_history')
    else:
        form = ProductImportForm()

    return render(request, 'shop/product_import.html', {'form': form})


def process_excel_import(import_task):
    try:
        # Читаем Excel
        df = pd.read_excel(import_task.file.path)

        success_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Создаем товар
                product = Product(
                    name=row['Название'],
                    description=row.get('Описание', ''),
                    short_description=row.get('Краткое описание', ''),
                    price=row['Цена'],
                    old_price=row.get('Старая цена'),
                    quantity=row.get('Количество', 0),
                    category=get_or_create_category(row.get('Категория', 'Разное')),
                    is_active=True
                )

                # Загружаем изображение
                image_url = row.get('Изображение')
                if image_url and pd.notna(image_url):
                    product.image = download_image(image_url, product.name)

                product.save()
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Строка {index + 2}: {str(e)}")

        # Обновляем статус импорта
        import_task.status = 'success'
        import_task.imported_count = success_count
        import_task.error_count = error_count
        import_task.errors = '\n'.join(errors)
        import_task.save()

    except Exception as e:
        import_task.status = 'error'
        import_task.errors = str(e)
        import_task.save()


def get_or_create_category(name):
    category, created = Category.objects.get_or_create(
        name=name,
        defaults={'slug': slugify(name), 'is_active': True}
    )
    return category


def download_image(url, product_name):
    """Загружает изображение по URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Создаем имя файла
        file_extension = url.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png', 'gif']:
            file_extension = 'jpg'

        filename = f"{slugify(product_name)}.{file_extension}"

        # Сохраняем изображение
        from io import BytesIO
        from django.core.files import File

        image_content = ContentFile(response.content)
        return File(image_content, name=filename)

    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return None