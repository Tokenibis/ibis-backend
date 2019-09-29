from django.urls import path
from .views import LoginView, IdentifyView, PaymentView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('identify/', IdentifyView.as_view(), name='identify'),
    path('payment/', PaymentView.as_view(), name='payment'),
]
