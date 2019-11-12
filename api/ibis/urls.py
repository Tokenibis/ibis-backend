from django.urls import path
from .views import LoginView, LogoutView, IdentifyView, PaymentView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('identify/', IdentifyView.as_view(), name='identify'),
    path('payment/', PaymentView.as_view(), name='payment'),
]
