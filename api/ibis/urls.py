from django.urls import path
from .views import LoginView, IdentifyView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('identify/', IdentifyView.as_view(), name='identify'),
]
