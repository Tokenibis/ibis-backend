from django.urls import path
import distribution.views as views

urlpatterns = [
    path('finance/', views.FinanceView.as_view(), name='finance'),
]
