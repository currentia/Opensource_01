from django.urls import path
from .views import group_list

app_name = 'groups'

urlpatterns = [
    path('', group_list, name='group_list'),
]
from .views import group_list, delete_group
urlpatterns = [
    path("", group_list, name="group_list"),

    path(
        "delete/<int:group_id>/",
        delete_group,
        name="delete_group"
    ),
]