from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 사용자가 '/' 접근 시 → ledger 앱의 first 뷰로
    path('', include('ledger.urls')),  # 맨처음 페이지
    path('accounts/', include('accounts.urls')), # 로그인 페이지
    path('friends/',  include('friends.urls')), # 친구 관련 페이지
    path('groups/', include('groups.urls')),

]
