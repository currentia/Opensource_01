from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser): #AbstractUser에 아이디, 패스워드가 들어가 있어서 상속 받은 상태
    name          = models.CharField(max_length=20)           # 이름
    birth         = models.DateField()                        # 생년월일
    daily_budget  = models.PositiveIntegerField(default=0)    # 하루 사용 목표 금액
    budget_updated_at = models.DateField(null=True, blank=True)  # 마지막 갱신일

    
class UserScore(models.Model): # 1:1 관계
    user    = models.OneToOneField(User, on_delete=models.CASCADE) # OneToOneField -> user가 삭제되면 userscore도 삭제
    score   = models.IntegerField(default=60)   # 기본 60점 시작 (수정 필요)
    updated = models.DateTimeField(auto_now=True) # 레코드가 저장될 때마다 자동으로 현재 시간을 기록

    def __str__(self):
        return f'{self.user.username} - {self.score}점'
    
    
class DailyAchievement(models.Model): # 1:N 관계
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements') # ForeignKey -> User 1명 : DailyAchievement N개
    date     = models.DateField()
    achieved = models.BooleanField()  # True: 달성 / False: 미달성

    class Meta:
        unique_together = ('user', 'date')  # 하루에 한 번만 기록, unique_together → (user, date) 조합이 유일해야 함

    def __str__(self):
        status = '달성' if self.achieved else '미달성'
        return f'{self.user.username} - {self.date} - {status}'
