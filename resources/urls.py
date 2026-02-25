from django.urls import path
from . import views

urlpatterns = [
    path('', views.resource_access, name='resource_access'),
    path('upload/', views.resource_upload, name='resource_upload'),
    path('<str:subject>/', views.resource_subject, name='resource_subject'),
]