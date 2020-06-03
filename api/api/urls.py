from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework_swagger.views import get_swagger_view
from graphene_django.views import GraphQLView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', get_swagger_view(title='Ibis API'), name='api'),
    path('auth/', include('users.urls')),
    path('accounts/', include('allauth.urls'), name='socialaccount_signup'),
    path('ibis/', include('ibis.urls')),
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path('notifications/', include('notifications.urls')),
    path('tracker/', include('tracker.urls')),
]
