from django.urls import path
from . import views

app_name = 'friends'

urlpatterns = [
    path('',                          views.friend_main,    name='friend_main'),
    path('request/',                  views.send_request,   name='send_request'),
    path('accept/<int:request_id>/',  views.accept_request, name='accept_request'),
    path('reject/<int:request_id>/',  views.reject_request, name='reject_request'),
]
