from django.urls import path
from . import views #.은 현재 파일을 의미, account/view.py을 가져옴

app_name = 'accounts'

urlpatterns = [
    path('login/',   views.login_view,  name='login'),
    path('logout/',  views.logout_view, name='logout'),
    path('signup/',  views.signup_view, name='signup'),
]