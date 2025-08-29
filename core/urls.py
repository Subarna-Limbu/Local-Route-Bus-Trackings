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
    path('api/toggle_seat/', views.toggle_seat, name='toggle_seat'),
    path('api/bookmark_bus/', views.bookmark_bus, name='bookmark_bus'),
    path('api/remove_bookmark/', views.remove_bookmark, name='remove_bookmark'),
    path('api/send_pickup/', views.send_pickup_request, name='send_pickup'),
    path('driver/notifications/', views.driver_notifications, name='driver_notifications'),
    path('api/mark_pickup_seen/', views.mark_pickup_seen, name='mark_pickup_seen'),
    path('api/clear_all_pickups/', views.clear_all_pickups, name='clear_all_pickups'),
    path('user/profile/<int:user_id>/', views.user_profile, name='user_profile'),
    path('messages/<int:other_user_id>/', views.fetch_messages, name='fetch_messages'),
    # custom logout view (accepts GET) for convenience
    path('logout/', views.logout_view, name='logout'),
]
