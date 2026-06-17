from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from ledger.models import Ledger
from django.utils import timezone
 
User = settings.AUTH_USER_MODEL
 
# ledger.models 의 CATEGORY_CHOICES 와 동기화
CATEGORY_CHOICES = Ledger.CATEGORY_CHOICES
 
# ──────────────────────────────────────────────
# 1. 모임 기본 정보
# ──────────────────────────────────────────────
class Group(models.Model):
    name       = models.CharField(max_length=50)
    owner      = models.ForeignKey(
                    User,
                    on_delete=models.CASCADE,
                    related_name='owned_groups'     # 내가 만든 모임
                 )
    end_date   = models.DateField()                 # 모임 종료일 (D-day 기준)
    max_members = models.PositiveIntegerField(
                    default=10,
                    validators=[MinValueValidator(2), MaxValueValidator(10)]
                 )
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'{self.name} (모임장: {self.owner.username})'
 
 
# ──────────────────────────────────────────────
# 2. 모임 멤버 (모임 점수 포함)
# ──────────────────────────────────────────────
class GroupMember(models.Model):
    group       = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    user        = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='group_memberships')
    group_score = models.IntegerField(default=0)    # 모임 점수: 0점 시작, 개인 점수와 완전 분리
    joined_at   = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('group', 'user')         # 같은 모임에 중복 가입 방지
 
    def __str__(self):
        return f'{self.group.name} - {self.user.username} ({self.group_score}점)'
 
 
# ──────────────────────────────────────────────
# 3. 모임 초대
# ──────────────────────────────────────────────
class GroupInvite(models.Model):
    STATUS_CHOICES = [
        ('pending',  '대기중'),
        ('accepted', '수락'),
        ('rejected', '거절'),
    ]
 
    group     = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    from_user = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='sent_group_invites')
    to_user   = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='received_group_invites')
    status    = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('group', 'to_user')      # 같은 모임에 중복 초대 방지
 
    def __str__(self):
        return f'[{self.group.name}] {self.from_user.username} → {self.to_user.username} ({self.status})'
 
 
# ──────────────────────────────────────────────
# 4. 기본 챌린지
# 모임 생성 시 목표 카테고리 선택 → 규칙 자동 설정
# 달성 기준: 하루 해당 카테고리 지출 / 하루 전체 지출 <= ratio_limit
# ──────────────────────────────────────────────
class Challenge(models.Model):
    group       = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='challenges')
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    ratio_limit = models.FloatField(
                    validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
                  )                                 # ex) 0.3 → 하루 지출의 30% 이하면 달성
    created_at  = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'[{self.group.name}] {self.get_category_display()} - {self.ratio_limit * 100:.0f}% 이하'
 
 
# ──────────────────────────────────────────────
# 5. 커스텀 챌린지
# 사용자가 직접 카테고리 + 금액 조건 등록
# ──────────────────────────────────────────────
class CustomChallenge(models.Model):
    group        = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='custom_challenges')
    created_by   = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='created_challenges')
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount_limit = models.PositiveIntegerField()    # 하루 해당 카테고리 지출이 이 금액 이하면 달성
    bonus_score  = models.PositiveSmallIntegerField(
                    default=1,
                    validators=[MinValueValidator(1), MaxValueValidator(5)]
                  )                                 # 달성 시 모임 점수 보너스 (1~5점)
    expires_date = models.DateField(default=timezone.now)              # 유효 기간: 등록 당일 23:59까지
    description  = models.CharField(max_length=100, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'[{self.group.name}] 커스텀 - {self.get_category_display()} {self.amount_limit}원 이하'
 
 
# ──────────────────────────────────────────────
# 6. 기본 챌린지 달성 결과 (일별)
# ──────────────────────────────────────────────
class BasicChallengeResult(models.Model):
    challenge   = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='results')
    user        = models.ForeignKey(User,      on_delete=models.CASCADE, related_name='basic_challenge_results')
    date        = models.DateField()
    is_achieved = models.BooleanField()
 
    class Meta:
        unique_together = ('challenge', 'user', 'date')  # 하루 1회만 기록
 
    def __str__(self):
        status = '달성' if self.is_achieved else '미달성'
        return f'[기본] {self.user.username} - {self.date} - {status}'
 
 
# ──────────────────────────────────────────────
# 7. 커스텀 챌린지 달성 결과 (일별)
# ──────────────────────────────────────────────
class CustomChallengeResult(models.Model):
    challenge   = models.ForeignKey(CustomChallenge, on_delete=models.CASCADE, related_name='results')
    user        = models.ForeignKey(User,            on_delete=models.CASCADE, related_name='custom_challenge_results')
    date        = models.DateField()
    is_achieved = models.BooleanField()
 
    class Meta:
        unique_together = ('challenge', 'user', 'date')  # 하루 1회만 기록
 
    def __str__(self):
        status = '달성' if self.is_achieved else '미달성'
        return f'[커스텀] {self.user.username} - {self.date} - {status}'
 
 
# ──────────────────────────────────────────────
# 8. 모임 내 연속 달성 추적
# accounts.DailyAchievement 와 동일한 역할, 모임 전용
# ──────────────────────────────────────────────
class GroupDailyAchievement(models.Model):
    group_member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='daily_achievements')
    date         = models.DateField()
    is_achieved  = models.BooleanField()
 
    class Meta:
        unique_together = ('group_member', 'date')       # 멤버당 하루 1회
 
    def __str__(self):
        status = '달성' if self.is_achieved else '미달성'
        return f'{self.group_member} - {self.date} - {status}'
 
 
# ──────────────────────────────────────────────
# 9. 모임 점수 변동 이력
# accounts.UserScore 와 동일한 역할, 모임 전용
# ──────────────────────────────────────────────
class GroupScoreHistory(models.Model):
    REASON_CHOICES = [
        ('daily_achieve',   '연속 달성'),
        ('daily_penalty',   '연속 미달성'),
        ('challenge_bonus', '챌린지 달성 보너스'),
        ('challenge_penalty', '챌린지 미달성 패널티'),
    ]
 
    group_member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='score_history')
    score_delta  = models.IntegerField()            # +점수 or -점수
    reason       = models.CharField(max_length=20, choices=REASON_CHOICES)
    created_at   = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        sign = '+' if self.score_delta >= 0 else ''
        return f'{self.group_member} - {sign}{self.score_delta} ({self.get_reason_display()})'
 
 
# ──────────────────────────────────────────────
# 10. 피드백 (하루 지출에 대한 코멘트)
# ──────────────────────────────────────────────
class Feedback(models.Model):
    group       = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='feedbacks')
    from_user   = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='sent_feedbacks')
    target_user = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='received_feedbacks')
    ledger_date = models.DateField()                # 피드백 대상 날짜 (하루 지출 단위)
    content     = models.CharField(max_length=200)
    created_at  = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'{self.from_user.username} → {self.target_user.username} ({self.ledger_date})'