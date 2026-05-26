from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending',  '대기중'),
        ('accepted', '수락'),
        ('rejected', '거절'),
    ]

    from_user  = models.ForeignKey(User, related_name='sent_requests',     on_delete=models.CASCADE) # 내가 보낸 요청
    to_user    = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE) # 내가 받은 요청
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending') 
    created_at = models.DateTimeField(auto_now_add=True) # auto_now_add=True -> 최초 생성 시에만 저장

    class Meta:
        # 같은 두 사람 사이에 중복 요청 방지
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f'{self.from_user.username} → {self.to_user.username} ({self.status})'
