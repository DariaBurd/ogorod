from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout  # ← добавила logout
from django.contrib import messages
from .forms import CustomerRegistrationForm, CustomerLoginForm
from .models import Product, Category
from django.utils.text import slugify  # ← добавила slugify
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Cart, CartItem, Order


def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.first_name}!')
            return redirect('shop:catalog')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})


def catalog(request):
    categories = Category.objects.filter(is_active=True)[:3]
    featured_products = Product.objects.filter(
        is_active=True,
        quantity__gt=0
    )[:8]
    return render(request, 'shop/catalog.html', {
        'categories': categories,
        'products': featured_products
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

                # Проверяем, есть ли параметр next для редиректа
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('shop:catalog')
    else:
        form = CustomerLoginForm()
    return render(request, 'shop/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы!')
    return redirect('shop:catalog')


from django.contrib.auth.decorators import login_required
from .models import ChatMessage


@login_required(login_url='/login/')
def chat_room(request):
    messages = ChatMessage.objects.all()[:50]
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
            process_excel_import(import_task)
            messages.success(request,
                             f'Импорт завершен! Успешно: {import_task.imported_count}, Ошибок: {import_task.error_count}')
            return redirect('shop:import_history')
    else:
        form = ProductImportForm()
    return render(request, 'shop/product_import.html', {'form': form})


def process_excel_import(import_task):
    try:
        df = pd.read_excel(import_task.file.path)
        success_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
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

                image_url = row.get('Изображение')
                if image_url and pd.notna(image_url):
                    product.image = download_image(image_url, product.name)

                product.save()
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Строка {index + 2}: {str(e)}")

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
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        file_extension = url.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png', 'gif']:
            file_extension = 'jpg'

        filename = f"{slugify(product_name)}.{file_extension}"

        from io import BytesIO
        from django.core.files import File

        image_content = ContentFile(response.content)
        return File(image_content, name=filename)

    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return None


def product_detail(request, product_id):
    """Детальная страница товара"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product_id)[:4]

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related_products': related_products
    })


def category_products(request, category_slug):
    """Товары в категории"""
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    products = Product.objects.filter(
        category=category,
        is_active=True,
        quantity__gt=0
    )

    return render(request, 'shop/category_products.html', {
        'category': category,
        'products': products
    })


@login_required
def profile(request):
    """Профиль пользователя"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')[:10]
    return render(request, 'shop/profile.html', {
        'user': request.user,
        'orders': orders
    })


def add_to_cart(request, product_id):
    """Добавление товара в корзину"""
    product = get_object_or_404(Product, id=product_id, is_active=True, quantity__gt=0)

    # Получаем или создаем корзину
    cart = get_or_create_cart(request)

    # Проверяем, есть ли товар уже в корзине
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )

    if not created:
        # Если товар уже есть, увеличиваем количество
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f'Товар "{product.name}" добавлен в корзину!')
    return redirect('shop:cart')


def remove_from_cart(request, item_id):
    """Удаление товара из корзины"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, 'Товар удален из корзины')
    return redirect('shop:cart')


def update_cart_item(request, item_id):
    """Обновление количества товара в корзине"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        cart_item = get_object_or_404(CartItem, id=item_id)

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Количество обновлено')
        else:
            cart_item.delete()
            messages.success(request, 'Товар удален из корзины')

    return redirect('shop:cart')


def cart_view(request):
    """Просмотр корзины"""
    cart = get_or_create_cart(request)

    return render(request, 'shop/cart.html', {
        'cart': cart,
        'cart_items': cart.items.all()
    })


def get_or_create_cart(request):
    """Получение или создание корзины для пользователя"""
    if request.user.is_authenticated:
        # Для авторизованных пользователей
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Для анонимных пользователей
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)

    return cart


@login_required
def checkout(request):
    """Оформление заказа"""
    cart = get_or_create_cart(request)

    if request.method == 'POST':
        # Создаем заказ
        order = Order.objects.create(
            customer=request.user,
            contact_phone=request.POST.get('phone', request.user.phone),
            delivery_address=request.POST.get('address', request.user.address),
            comment=request.POST.get('comment', ''),
            status='new'
        )

        # Переносим товары из корзины в заказ
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )

        # Очищаем корзину
        cart.items.all().delete()
        cart.delete()

        messages.success(request, f'Заказ #{order.id} успешно оформлен!')
        return redirect('shop:profile')

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'user': request.user
    })