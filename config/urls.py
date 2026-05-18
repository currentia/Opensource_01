from django.contrib import admin
from django.urls import path
from .views import login_view, main_view, register_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view),
    path('main/', main_view),
    path('register/', register_view),
    path('logout/', logout_view),
]
