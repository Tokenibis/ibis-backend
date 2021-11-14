from django.urls import path
import distribution.views as views

urlpatterns = [
    path('finance/', views.FinanceView.as_view(), name='finance'),
    path('amount/', views.AmountView.as_view(), name='amount'),
    path('report/<slug:pk>/', views.ReportView.as_view(), name='report'),
]
