from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import json
from django.contrib.auth.models import BaseUserManager


class CustomerManager(BaseUserManager):
    def create_user(self, email, phone, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        if not phone:
            raise ValueError('Телефон обязателен')

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(email, phone, first_name, last_name, password, **extra_fields)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class Customer(AbstractUser):
    objects = CustomerManager()
    phone = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Номер телефона'
    )
    patronymic = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Отчество'
    )

    # Используем email как логин для входа
    username = None
    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия'
    )

    # Дополнительные поля для клиента
    address = models.TextField(
        blank=True,
        verbose_name='Адрес доставки'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации'
    )

    USERNAME_FIELD = 'email'  # Вход по email
    REQUIRED_FIELDS = ['phone', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.phone})"

    def get_full_name(self):
        """Возвращает полное имя с отчеством"""
        if self.patronymic:
            return f"{self.last_name} {self.first_name} {self.patronymic}"
        return f"{self.last_name} {self.first_name}"

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']


class Category(models.Model):
    """Категории товаров"""
    name = models.CharField(
        max_length=100,
        verbose_name='Название категории'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='URL-идентификатор'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание категории'
    )
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        verbose_name='Изображение категории'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']


class Product(models.Model):
    """Товары магазина"""
    name = models.CharField(
        max_length=200,
        verbose_name='Название товара'
    )
    description = models.TextField(
        verbose_name='Описание товара'
    )
    short_description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Краткое описание'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Старая цена'
    )
    quantity = models.IntegerField(
        default=0,
        verbose_name='Количество на складе'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name='Категория',
        related_name='products'
    )
    image = models.ImageField(
        upload_to='products/',
        verbose_name='Главное изображение'
    )
    additional_images = models.ManyToManyField(
        'ProductImage',
        blank=True,
        verbose_name='Дополнительные изображения',
        related_name='additional_products'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Рекомендуемый товар'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    @property
    def available(self):
        """Доступен ли товар для заказа"""
        return self.is_active and self.quantity > 0

    @property
    def has_discount(self):
        """Есть ли скидка на товар"""
        return self.old_price and self.old_price > self.price

    @property
    def discount_percent(self):
        """Процент скидки"""
        if self.has_discount:
            return int((1 - self.price / self.old_price) * 100)
        return 0

    def clean(self):
        """Валидация данных"""
        if self.quantity < 0:
            raise ValidationError('Количество не может быть отрицательным')
        if self.price < 0:
            raise ValidationError('Цена не может быть отрицательной')

    def __str__(self):
        return f"{self.name} ({self.quantity} шт.)"

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']


class ProductImage(models.Model):
    """Дополнительные изображения товаров"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='products/additional/',
        verbose_name='Изображение'
    )
    alt_text = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Альтернативный текст'
    )
    order = models.IntegerField(
        default=0,
        verbose_name='Порядок отображения'
    )

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['order']


class Order(models.Model):
    """Заказы клиентов"""
    STATUS_CHOICES = [
        ('new', '🆕 Новый'),
        ('confirmed', '✅ Подтвержден'),
        ('cancelled', '❌ Отменен'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        verbose_name='Клиент',
        related_name='orders'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='Статус'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Сумма заказа'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий клиента'
    )
    admin_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий администратора'
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Контактный телефон для заказа'
    )
    delivery_address = models.TextField(
        blank=True,
        verbose_name='Адрес доставки'
    )

    def update_status(self, new_status, admin_comment=''):
        """Безопасное изменение статуса с управлением количеством товаров"""
        if self.status == new_status:
            return

        old_status = self.status

        # Логика изменения количества товаров
        if new_status == 'confirmed' and old_status != 'confirmed':
            # Подтверждаем заказ - списываем товары
            for item in self.items.all():
                if item.quantity > item.product.quantity:
                    raise ValidationError(
                        f"Недостаточно товара '{item.product.name}'. "
                        f"На складе: {item.product.quantity}, в заказе: {item.quantity}"
                    )

                item.product.quantity -= item.quantity
                item.product.save()

                # Отправляем уведомление в Telegram
                self._send_telegram_notification(f"✅ Заказ #{self.id} подтвержден")

        elif new_status == 'cancelled' and old_status != 'cancelled':
            # Отменяем заказ - возвращаем товары
            for item in self.items.all():
                item.product.quantity += item.quantity
                item.product.save()

            # Отправляем уведомление в Telegram
            self._send_telegram_notification(f"❌ Заказ #{self.id} отменен")

        self.status = new_status
        self.admin_comment = admin_comment
        self.save()

        # Отправляем уведомление о создании нового заказа
        if old_status == 'new' and new_status == 'new':
            self._send_new_order_notification()

    def _send_new_order_notification(self):
        """Отправка уведомления о новом заказе в Telegram"""
        message = f"""
🆕 НОВЫЙ ЗАКАЗ #{self.id}

👤 Клиент: {self.customer.get_full_name()}
📞 Телефон: {self.contact_phone or self.customer.phone}
💰 Сумма: {self.total_amount} руб.
📦 Товаров: {self.items.count()} шт.

💬 Комментарий: {self.comment or 'нет'}

🛠 Для управления заказом перейдите в админ-панель:
{settings.SITE_URL}/admin/shop/order/{self.id}/change/
        """
        self._send_telegram_message(message)

    def _send_telegram_notification(self, status_text):
        """Отправка уведомления об изменении статуса"""
        message = f"""
{status_text}

📦 Заказ #{self.id}
👤 Клиент: {self.customer.get_full_name()}
💰 Сумма: {self.total_amount} руб.
        """
        self._send_telegram_message(message)

    def _send_telegram_message(self, message):
        """Отправка сообщения в Telegram"""
        if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and hasattr(settings, 'TELEGRAM_CHAT_ID'):
            try:
                url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': settings.TELEGRAM_CHAT_ID,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                requests.post(url, json=payload, timeout=10)
            except Exception as e:
                # Логируем ошибку, но не прерываем выполнение
                print(f"Ошибка отправки в Telegram: {e}")

    def save(self, *args, **kwargs):
        # Пересчет суммы при сохранении
        if self.pk:
            self.total_amount = sum(item.total_price for item in self.items.all())

        # Устанавливаем контактный телефон если не указан
        if not self.contact_phone:
            self.contact_phone = self.customer.phone

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ #{self.id} от {self.customer} ({self.get_status_display()})"

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class OrderItem(models.Model):
    """Позиции в заказе"""
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    quantity = models.IntegerField(
        default=1,
        verbose_name='Количество'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена на момент заказа'
    )

    @property
    def total_price(self):
        """Общая стоимость позиции"""
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        # Устанавливаем цену товара на момент создания
        if not self.pk:
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'


class Cart(models.Model):
    """Корзина покупок"""
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name='Ключ сессии'
    )
    user = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Пользователь',
        related_name='carts'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    @property
    def total_amount(self):
        """Общая сумма корзины"""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_quantity(self):
        """Общее количество товаров в корзине"""
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        if self.user:
            return f"Корзина {self.user}"
        return f"Корзина (анонимная)"

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'


class CartItem(models.Model):
    """Позиции в корзине"""
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='Корзина'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    quantity = models.IntegerField(
        default=1,
        verbose_name='Количество'
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    @property
    def total_price(self):
        """Общая стоимость позиции"""
        return self.product.price * self.quantity

    def clean(self):
        """Проверка доступности товара"""
        if self.quantity > self.product.quantity:
            raise ValidationError(
                f"Недостаточно товара '{self.product.name}'. "
                f"Доступно: {self.product.quantity}"
            )

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    class Meta:
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'
        unique_together = ['cart', 'product']