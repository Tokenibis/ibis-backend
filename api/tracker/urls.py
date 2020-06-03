from django.urls import path
import tracker.views as views

urlpatterns = [
    path('wait/', views.WaitView.as_view(), name='wait'),
]
