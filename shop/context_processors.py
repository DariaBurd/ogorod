from .models import Cart


def cart_context(request):
    """Добавляет корзину в контекст всех шаблонов"""
    cart = None

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key, user=None).first()

    return {
        'cart': cart
    }