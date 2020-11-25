from django.urls import path
import ibis.views as views

urlpatterns = [
    path('price/', views.PriceView.as_view(), name='price'),
    path('quote/', views.QuoteView.as_view(), name='quote'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('login-anon/', views.AnonymousLoginView.as_view(), name='login-anon'),
    path('login-pass/', views.PasswordLoginView.as_view(), name='login-pass'),
    path(
        'change-pass/', views.PasswordChangeView.as_view(),
        name='change-pass'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('identify/', views.IdentifyView.as_view(), name='identify'),
    path('payment/', views.PaymentView.as_view(), name='payment'),
]
