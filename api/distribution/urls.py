from django.urls import path
import distribution.views as views

urlpatterns = [
    path('amount/', views.AmountView.as_view(), name='amount'),
    path('payment/', views.PaymentView.as_view(), name='payment'),
    path('investment/', views.InvestmentView.as_view(), name='investment'),
]
