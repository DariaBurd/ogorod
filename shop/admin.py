from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *


class CustomerAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'phone', 'order_count', 'created_at']
    list_filter = ['created_at', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'patronymic', 'phone', 'address')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    def order_count(self, obj):
        return obj.orders.count()

    order_count.short_description = 'Количество заказов'


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = 'Количество товаров'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'old_price', 'quantity', 'available', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'quantity', 'is_featured']
    readonly_fields = ['created_at', 'updated_at', 'discount_percent_display']
    inlines = [ProductImageInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'description', 'short_description')
        }),
        ('Цены и количество', {
            'fields': ('price', 'old_price', 'discount_percent_display', 'quantity')
        }),
        ('Изображения', {
            'fields': ('image',)
        }),
        ('Настройки', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    change_list_template = 'admin/shop/product/change_list.html'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel_view), name='product_import_excel'),
        ]
        return custom_urls + urls

    def import_excel_view(self, request):
        """Представление для импорта Excel"""
        from django.shortcuts import render, redirect
        from django.contrib import messages
        import pandas as pd
        import requests
        from io import BytesIO
        from django.core.files.base import ContentFile
        from django.core.files import File

        if request.method == 'POST' and request.FILES.get('excel_file'):
            try:
                excel_file = request.FILES['excel_file']

                # Проверяем расширение
                if not excel_file.name.endswith(('.xlsx', '.xls')):
                    messages.error(request, 'Поддерживаются только файлы Excel (.xlsx, .xls)')
                    return redirect('admin:shop_product_changelist')

                # Читаем Excel
                df = pd.read_excel(excel_file)

                created_count = 0
                error_count = 0

                for index, row in df.iterrows():
                    try:
                        # Получаем или создаем категорию
                        category_name = row.get('Категория', 'Разное')
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'slug': category_name.lower().replace(' ', '-'), 'is_active': True}
                        )

                        # Создаем товар
                        product = Product(
                            name=row['Название'],
                            description=str(row.get('Описание', '')),
                            short_description=str(row.get('Краткое описание', '')),
                            price=float(row['Цена']),
                            old_price=float(row.get('Старая цена', 0)) if pd.notna(row.get('Старая цена')) else None,
                            quantity=int(row.get('Количество', 0)),
                            category=category,
                            is_active=True
                        )

                        # Загружаем изображение если есть URL
                        image_url = row.get('Изображение')
                        if pd.notna(image_url) and str(image_url).startswith('http'):
                            try:
                                response = requests.get(str(image_url), timeout=10)
                                if response.status_code == 200:
                                    # Генерируем имя файла
                                    file_extension = str(image_url).split('.')[-1].lower()
                                    if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                                        file_extension = 'jpg'

                                    filename = f"{product.name.lower().replace(' ', '_')}_{index}.{file_extension}"
                                    image_content = ContentFile(response.content)
                                    product.image.save(filename, File(image_content))
                            except:
                                pass

                        product.save()
                        created_count += 1

                    except Exception as e:
                        error_count += 1
                        print(f"Ошибка в строке {index}: {e}")

                messages.success(request, f'✅ Импорт завершен! Создано товаров: {created_count}, Ошибок: {error_count}')

            except Exception as e:
                messages.error(request, f'❌ Ошибка при обработке файла: {str(e)}')

            return redirect('admin:shop_product_changelist')

        return render(request, 'admin/shop/import_form.html')

    def discount_percent_display(self, obj):
        if obj.has_discount:
            return f"{obj.discount_percent}%"
        return "—"

    discount_percent_display.short_description = 'Скидка'

    def available(self, obj):
        return obj.available

    available.boolean = True
    available.short_description = 'Доступен'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'total_price']
    fields = ['product', 'quantity', 'price', 'total_price']

    def total_price(self, obj):
        return f"{obj.total_price} руб."

    total_price.short_description = 'Сумма'


class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_display', 'total_amount_display', 'status_display', 'created_at', 'action_buttons']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'customer__email', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['id', 'customer', 'created_at', 'updated_at', 'total_amount', 'contact_phone',
                       'delivery_address']
    inlines = [OrderItemInline]
    actions = ['confirm_orders', 'cancel_orders']

    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'customer', 'status', 'total_amount', 'created_at', 'updated_at')
        }),
        ('Контактные данные', {
            'fields': ('contact_phone', 'delivery_address')
        }),
        ('Комментарии', {
            'fields': ('comment', 'admin_comment')
        }),
    )

    def customer_display(self, obj):
        return f"{obj.customer.get_full_name()} ({obj.customer.phone})"

    customer_display.short_description = 'Клиент'

    def total_amount_display(self, obj):
        return f"{obj.total_amount} руб."

    total_amount_display.short_description = 'Сумма'

    def status_display(self, obj):
        status_colors = {
            'new': 'orange',
            'confirmed': 'green',
            'cancelled': 'red'
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = 'Статус'

    def action_buttons(self, obj):
        if obj.status == 'new':
            return format_html(
                '''
                <a href="{}" class="button" style="background: green; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;">✅ Подтвердить</a>
                <a href="{}" class="button" style="background: red; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">❌ Отменить</a>
                ''',
                f"{obj.id}/confirm/",
                f"{obj.id}/cancel/"
            )
        return "—"

    action_buttons.short_description = 'Действия'
    action_buttons.allow_tags = True

    def confirm_orders(self, request, queryset):
        for order in queryset:
            if order.status == 'new':
                order.update_status('confirmed', 'Подтверждено массово через админку')
        self.message_user(request, f"{queryset.count()} заказов подтверждено")

    confirm_orders.short_description = '✅ Подтвердить выбранные заказы'

    def cancel_orders(self, request, queryset):
        for order in queryset:
            if order.status == 'new':
                order.update_status('cancelled', 'Отменено массово через админку')
        self.message_user(request, f"{queryset.count()} заказов отменено")

    cancel_orders.short_description = '❌ Отменить выбранные заказы'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/confirm/', self.admin_site.admin_view(self.confirm_order),
                 name='shop_order_confirm'),
            path('<path:object_id>/cancel/', self.admin_site.admin_view(self.cancel_order), name='shop_order_cancel'),
        ]
        return custom_urls + urls

    def confirm_order(self, request, object_id):
        from django.shortcuts import redirect
        order = Order.objects.get(id=object_id)
        if order.status == 'new':
            order.update_status('confirmed', 'Подтверждено через админку')
            self.message_user(request, f'Заказ #{order.id} подтвержден')
        return redirect('admin:shop_order_changelist')

    def cancel_order(self, request, object_id):
        from django.shortcuts import redirect
        order = Order.objects.get(id=object_id)
        if order.status == 'new':
            order.update_status('cancelled', 'Отменено через админку')
            self.message_user(request, f'Заказ #{order.id} отменен')
        return redirect('admin:shop_order_changelist')


class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_display', 'total_quantity', 'total_amount_display', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']

    def user_display(self, obj):
        if obj.user:
            return str(obj.user)
        return f"Аноним ({obj.session_key})"

    user_display.short_description = 'Пользователь'

    def total_amount_display(self, obj):
        return f"{obj.total_amount} руб."

    total_amount_display.short_description = 'Сумма'


class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'total_price_display']
    list_filter = ['cart__user']

    def total_price_display(self, obj):
        return f"{obj.total_price} руб."

    total_price_display.short_description = 'Сумма'


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'total_price_display']
    list_filter = ['order__status']

    def total_price_display(self, obj):
        return f"{obj.total_price} руб."

    total_price_display.short_description = 'Сумма'


class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'alt_text', 'order']
    list_editable = ['order']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "—"

    image_preview.short_description = 'Превью'

    class ChatMessageAdmin(admin.ModelAdmin):
        list_display = ['user', 'message_short', 'created_at', 'is_read']
        list_filter = ['created_at', 'is_read']
        search_fields = ['user__first_name', 'user__last_name', 'message']

        def message_short(self, obj):
            return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message

        message_short.short_description = 'Сообщение'

    admin.site.register(ChatMessage, ChatMessageAdmin)



admin.site.register(Customer, CustomerAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(ProductImage, ProductImageAdmin)


admin.site.site_header = 'Панель управления магазином'
admin.site.site_title = 'Магазин садовых товаров'
admin.site.index_title = 'Добро пожаловать в панель управления!'