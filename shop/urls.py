from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.catalog, name='catalog'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_login, name='logout'),
    path('chat/', views.chat_room, name='chat_room'),
    path('chat/send/', views.send_message, name='send_message'),
    path('import/products/', views.product_import, name='product_import'),
    #path('import/history/', views.import_history, name='import_history'),
]