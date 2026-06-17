from datetime import date, timedelta
from django.db.models import Sum
from .models import (
    GroupMember,
    GroupDailyAchievement,
    GroupScoreHistory,
    BasicChallengeResult,
    CustomChallengeResult,
    Challenge,
    CustomChallenge,
)
from ledger.models import Ledger


# ──────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────

def _get_member(group, user):
    """group + user → GroupMember 반환 (없으면 None)"""
    try:
        return GroupMember.objects.get(group=group, user=user)
    except GroupMember.DoesNotExist:
        return None


def _apply_score(member, delta, reason):
    """
    GroupMember 점수 반영 + 이력 저장
    - delta  : +정수 or -정수
    - reason : GroupScoreHistory.REASON_CHOICES 키값
    """
    member.group_score += delta
    member.save(update_fields=['group_score'])

    GroupScoreHistory.objects.create(
        group_member=member,
        score_delta=delta,
        reason=reason,
    )


# ──────────────────────────────────────────────
# 1. 기본 챌린지 달성 여부 판정
# 하루 해당 카테고리 지출 / 하루 전체 지출 <= ratio_limit
# ──────────────────────────────────────────────

def evaluate_basic_challenge(user, target_date):
    """
    해당 날짜의 기본 챌린지 달성 여부를 판정하고 BasicChallengeResult 에 저장
    - 유저가 속한 모든 모임의 기본 챌린지를 순회
    """
    # 하루 전체 지출
    total_spent = Ledger.objects.filter(
        user=user,
        date=target_date,
    ).aggregate(total=Sum('amount'))['total'] or 0

    # 전체 지출이 0이면 판정 불가 → 미달성 처리
    if total_spent == 0:
        memberships = GroupMember.objects.filter(user=user).select_related('group')
        for member in memberships:
            for challenge in member.group.challenges.all():
                BasicChallengeResult.objects.update_or_create(
                    challenge=challenge,
                    user=user,
                    date=target_date,
                    defaults={'is_achieved': False},
                )
        return

    memberships = GroupMember.objects.filter(user=user).select_related('group')

    for member in memberships:
        for challenge in member.group.challenges.all():
            # 해당 카테고리 하루 지출
            category_spent = Ledger.objects.filter(
                user=user,
                date=target_date,
                category=challenge.category,
            ).aggregate(total=Sum('amount'))['total'] or 0

            ratio = category_spent / total_spent
            is_achieved = ratio <= challenge.ratio_limit

            BasicChallengeResult.objects.update_or_create(
                challenge=challenge,
                user=user,
                date=target_date,
                defaults={'is_achieved': is_achieved},
            )


# ──────────────────────────────────────────────
# 2. 커스텀 챌린지 달성 여부 판정
# 하루 해당 카테고리 지출 <= amount_limit
# ──────────────────────────────────────────────

def evaluate_custom_challenge(user, target_date):
    """
    해당 날짜의 커스텀 챌린지 달성 여부를 판정하고 CustomChallengeResult 에 저장
    - expires_date 가 target_date 와 다르면 (당일이 아니면) 건너뜀
    """
    memberships = GroupMember.objects.filter(user=user).select_related('group')

    for member in memberships:
        for challenge in member.group.custom_challenges.all():
            # 유효 기간 체크: 등록 당일에만 판정
            if challenge.expires_date != target_date:
                continue

            category_spent = Ledger.objects.filter(
                user=user,
                date=target_date,
                category=challenge.category,
            ).aggregate(total=Sum('amount'))['total'] or 0

            is_achieved = category_spent <= challenge.amount_limit

            CustomChallengeResult.objects.update_or_create(
                challenge=challenge,
                user=user,
                date=target_date,
                defaults={'is_achieved': is_achieved},
            )


# ──────────────────────────────────────────────
# 3. 모임 내 하루 달성 여부 기록
# 기본 + 커스텀 챌린지 전부 달성해야 그날 달성으로 인정
# ──────────────────────────────────────────────

def record_group_achievement(user, target_date):
    """
    모든 챌린지(기본 + 커스텀) 달성 여부를 종합해
    GroupDailyAchievement 에 저장
    - 기본 챌린지 하나라도 미달성 → 미달성
    - 커스텀 챌린지 하나라도 미달성 → 미달성
    - 챌린지가 아예 없는 모임 → 달성으로 처리
    """
    memberships = GroupMember.objects.filter(user=user).select_related('group')

    for member in memberships:
        group = member.group

        # 기본 챌린지 결과 확인
        basic_results = BasicChallengeResult.objects.filter(
            challenge__group=group,
            user=user,
            date=target_date,
        )
        basic_failed = basic_results.filter(is_achieved=False).exists()

        # 커스텀 챌린지 결과 확인
        custom_results = CustomChallengeResult.objects.filter(
            challenge__group=group,
            user=user,
            date=target_date,
        )
        custom_failed = custom_results.filter(is_achieved=False).exists()

        is_achieved = not basic_failed and not custom_failed

        GroupDailyAchievement.objects.update_or_create(
            group_member=member,
            date=target_date,
            defaults={'is_achieved': is_achieved},
        )


# ──────────────────────────────────────────────
# 4. 모임 점수 업데이트
# accounts/services.py 의 check_and_update_score 와 동일한 구조
# 10일 연속 달성 → +1점 / 10일 연속 미달성 → -1점
# ──────────────────────────────────────────────

def check_and_update_group_score(user, group):
    """
    최근 10일 연속 달성/미달성 여부를 확인하고 모임 점수를 업데이트
    """
    member = _get_member(group, user)
    if not member:
        return

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(10)]

    records = GroupDailyAchievement.objects.filter(
        group_member=member,
        date__in=dates,
    ).values_list('date', 'is_achieved')

    record_dict = {r[0]: r[1] for r in records}

    # 10일치 데이터가 없으면 점수 변동 없음
    if len(record_dict) < 10:
        return

    # 10일 연속 달성
    if all(record_dict.get(d) == True for d in dates):
        _apply_score(member, +1, 'daily_achieve')

    # 10일 연속 미달성
    elif all(record_dict.get(d) == False for d in dates):
        _apply_score(member, -1, 'daily_penalty')


# ──────────────────────────────────────────────
# 5. 챌린지 보너스 / 패널티 점수
# 모임 종료일 기준으로 최종 달성률 계산 후 점수 반영
# ──────────────────────────────────────────────

def apply_challenge_score(user, group):
    """
    모임 종료 시 커스텀 챌린지 달성 결과에 따라 bonus_score 반영
    - 달성(is_achieved=True)한 커스텀 챌린지의 bonus_score 합산 → 모임 점수에 추가
    - 기본 챌린지 달성률 기준 패널티는 유지 (달성률 < 0.5 → -2점)
    """
    member = _get_member(group, user)
    if not member:
        return

    # 커스텀 챌린지 달성 보너스 합산
    achieved_custom = CustomChallengeResult.objects.filter(
        challenge__group=group,
        user=user,
        is_achieved=True,
    ).select_related('challenge')

    bonus_total = sum(r.challenge.bonus_score for r in achieved_custom)
    if bonus_total > 0:
        _apply_score(member, bonus_total, 'challenge_bonus')

    # 기본 챌린지 달성률 기반 패널티
    total = GroupDailyAchievement.objects.filter(group_member=member).count()
    if total == 0:
        return

    achieved = GroupDailyAchievement.objects.filter(
        group_member=member,
        is_achieved=True,
    ).count()

    ratio = achieved / total
    if ratio < 0.5:
        _apply_score(member, -2, 'challenge_penalty')


# ──────────────────────────────────────────────
# 6. 지출 저장 시 진입점
# ledger/views.py 의 지출 저장 로직에서 호출
# ──────────────────────────────────────────────

def record_group_daily(user, target_date):
    """
    하루 지출 저장 시 호출되는 진입점
    1. 기본 챌린지 판정
    2. 커스텀 챌린지 판정
    3. 모임 달성 여부 기록
    4. 모임 점수 업데이트 (10일 연속 체크)
    """
    evaluate_basic_challenge(user, target_date)
    evaluate_custom_challenge(user, target_date)
    record_group_achievement(user, target_date)

    # 유저가 속한 모든 모임에 대해 점수 체크
    memberships = GroupMember.objects.filter(user=user).select_related('group')
    for member in memberships:
        check_and_update_group_score(user, member.group)


# ──────────────────────────────────────────────
# 7. 모임 랭킹 조회
# ──────────────────────────────────────────────

def get_group_ranking(group):
    """
    모임 내 멤버 점수 순위 반환
    반환 형태: [{'rank': 1, 'user': ..., 'score': ...}, ...]
    """
    members = GroupMember.objects.filter(
        group=group,
    ).select_related('user').order_by('-group_score')

    ranking = []
    for idx, member in enumerate(members, start=1):
        ranking.append({
            'rank':  idx,
            'user':  member.user,
            'score': member.group_score,
        })
    return ranking


# ──────────────────────────────────────────────
# 8. 연속 달성 정보 조회
# accounts/services.py 의 get_streak_info 와 동일한 구조
# ──────────────────────────────────────────────

def get_group_streak_info(user, group):
    """
    모임 내 연속 달성/미달성 일수 반환
    """
    member = _get_member(group, user)
    if not member:
        return {'streak_achieved': 0, 'streak_failed': 0}

    today = date.today()
    streak_achieved = 0
    streak_failed   = 0

    for i in range(10):
        d = today - timedelta(days=i)
        try:
            record = GroupDailyAchievement.objects.get(group_member=member, date=d)
            if i == 0:
                if record.is_achieved:
                    streak_achieved += 1
                else:
                    streak_failed += 1
            else:
                if record.is_achieved and streak_achieved > 0:
                    streak_achieved += 1
                elif not record.is_achieved and streak_failed > 0:
                    streak_failed += 1
                else:
                    break
        except GroupDailyAchievement.DoesNotExist:
            break

    return {
        'streak_achieved': streak_achieved,
        'streak_failed':   streak_failed,
    }