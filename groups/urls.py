from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # ── 모임 기본 ──────────────────────────────
    path('',                                views.group_list,              name='group_list'),
    path('create/',                         views.group_create,            name='group_create'),
    path('<int:group_id>/',                 views.group_detail,            name='group_detail'),
    path('<int:group_id>/close/',           views.group_close,             name='group_close'),

    # ── 초대 ───────────────────────────────────
    path('<int:group_id>/invite/',                        views.group_invite,          name='group_invite'),
    path('invite/<int:invite_id>/<str:action>/',          views.group_invite_respond,  name='group_invite_respond'),

    # ── 챌린지 ─────────────────────────────────
    path('<int:group_id>/challenge/create/',              views.custom_challenge_create, name='custom_challenge_create'),
    path('<int:group_id>/challenge/<int:challenge_id>/delete/', views.custom_challenge_delete, name='custom_challenge_delete'),

    # ── 멤버 지출 조회 + 피드백 ────────────────
    path('<int:group_id>/ledger/<int:user_id>/<str:ledger_date>/', views.member_ledger,   name='member_ledger'),
    path('<int:group_id>/feedback/',                      views.feedback_create,       name='feedback_create'),
]
