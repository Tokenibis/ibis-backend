from django.contrib import admin
from django.urls import path, include
from rest_framework_swagger.views import get_swagger_view
from graphene_django.views import GraphQLView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', get_swagger_view(title='Ibis API'), name='api'),
    path('auth/', include('users.urls')),
    path('graphql/', GraphQLView.as_view(graphiql=True)),
]
