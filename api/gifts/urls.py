from django.urls import path
import gifts.views as views

urlpatterns = [
    path('choose/<int:pk>/', views.ChooseView.as_view(), name='gift_choose'),
    path('success/', views.SuccessView.as_view(), name='gift_success'),
    path('error/', views.ErrorView.as_view(), name='gift_error'),
]
