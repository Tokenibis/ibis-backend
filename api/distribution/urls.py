from django.urls import path
import distribution.views as views

urlpatterns = [
    path('amount/', views.AmountView.as_view(), name='amount'),
]
