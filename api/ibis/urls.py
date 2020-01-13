from django.urls import path
import ibis.views as views

urlpatterns = [
    path('price/', views.PriceView.as_view(), name='quote'),
    path('quote/', views.QuoteView.as_view(), name='quote'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('login-anon/', views.AnonymousLoginView.as_view(), name='login-anon'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('identify/', views.IdentifyView.as_view(), name='identify'),
    path('payment/', views.PaymentView.as_view(), name='payment'),
]
