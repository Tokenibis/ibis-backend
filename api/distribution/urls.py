from django.urls import path
import distribution.views as views

urlpatterns = [
    path('finance/', views.FinanceView.as_view(), name='finance'),
    path('amount/', views.AmountView.as_view(), name='amount'),
    path('report/', views.ReportView.as_view(), name='report'),
    path('grants/', views.GrantView.as_view(), name='grant'),
    path('logos/', views.LogoView.as_view(), name='logos'),
    path('video/', views.VideoView.as_view(), name='video'),
]
