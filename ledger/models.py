from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Ledger(models.Model):
    CATEGORY_CHOICES = [
        ('food',      '식비'),
        ('transport', '교통비'),
        ('leisure',   '여가비'),
        ('other',     '기타'),
        # 다른 카테고리 추가 예정
    ]

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ledgers')
    date     = models.DateField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount   = models.PositiveIntegerField()
    memo     = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.get_category_display()} - {self.amount}원'
