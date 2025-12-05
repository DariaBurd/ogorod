from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.catalog, name='catalog'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),  # ← профиль
    path('chat/', views.chat_room, name='chat_room'),
    path('chat/send/', views.send_message, name='send_message'),

    # Товары и категории
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<slug:category_slug>/', views.category_products, name='category_products'),

    # Корзина
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout, name='checkout'),

    # Импорт
    path('import/products/', views.product_import, name='product_import'),
    # path('import/history/', views.import_history, name='import_history'),
]