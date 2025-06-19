from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('driver/register/', views.driver_register, name='driver_register'),
    path('driver/login/', views.driver_login, name='driver_login'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('api/update_location/', views.update_location, name='update_location'),
    path('user/login/', views.user_login, name='user_login'),
    path('user/register/', views.user_register, name='user_register'),
    path('track/<int:bus_id>/', views.track_bus, name='track_bus'),
]
