from django.urls import path
from . import views

app_name = 'ledger'

urlpatterns = [
    path('',                                          views.first,  name='first'),
    path('main/',                                     views.main,   name='main'),
    path('main/<int:year>/<int:month>/<int:day>/',    views.detail, name='detail'),
]
