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
# ──────────────────────────────────────────────

def _calc_base_score(ratio):
    """
    기본 챌린지 사용 비율 → 기본 점수 반환
    ratio: 하루 해당 카테고리 지출 / 하루 전체 지출
    """
    if ratio == 0:
        return 3, True          # 0% 사용 → +3점, 보너스 제한 플래그
    elif ratio <= 0.30:
        return 3, False         # 1~30% 사용 → +3점
    elif ratio <= 0.50:
        return 4, False         # 30~50% 사용 → +4점
    elif ratio <= 0.80:
        return 5, False         # 50~80% 사용 → +5점 (최고 구간)
    elif ratio <= 1.00:
        return 3, False         # 80~100% 사용 → +3점
    elif ratio <= 1.20:
        return -3, False        # 100~120% 사용 → -3점
    else:
        return -5, False        # 120% 초과 → -5점


def _calc_streak_bonus(member, today):
    """
    연속 달성/미달성 일수를 계산해 보너스/패널티 반환
    달성: 3일 → +1점 / 5일 → +2점
    미달성: 3일 → -3점 / 5일 → -5점
    """
    achieved_streak = 0
    failed_streak = 0

    for i in range(5):
        d = today - timedelta(days=i)
        try:
            record = GroupDailyAchievement.objects.get(group_member=member, date=d)
            if i == 0:
                if record.is_achieved:
                    achieved_streak += 1
                else:
                    failed_streak += 1
            else:
                if record.is_achieved and achieved_streak > 0:
                    achieved_streak += 1
                elif not record.is_achieved and failed_streak > 0:
                    failed_streak += 1
                else:
                    break
        except GroupDailyAchievement.DoesNotExist:
            break

    bonus = 0
    if achieved_streak >= 5:
        bonus = +2
    elif achieved_streak >= 3:
        bonus = +1
    elif failed_streak >= 5:
        bonus = -5
    elif failed_streak >= 3:
        bonus = -3

    return bonus


def check_and_update_group_score(user, group, target_date):
    """
    하루 지출 저장 시 호출 — 모임 점수 업데이트
    1. 기본 챌린지 사용 비율 → 기본 점수 산출
    2. 연속 달성/미달성 보너스/패널티 합산
    3. 하루 최대 +10점 캡 적용 (음수는 캡 없음)
    4. 0% 달성 시 보너스 점수 제한 (기본 점수만)
    5. 감쇠 공식 적용: raw × (100 - 현재점수) / 30
    6. 0~100 클램핑
    """
    member = _get_member(group, user)
    if not member:
        return

    # 기본 챌린지 카테고리 및 ratio 계산
    base_challenge = group.challenges.first()
    if not base_challenge:
        return

    total_spent = Ledger.objects.filter(
        user=user,
        date=target_date,
    ).aggregate(total=Sum('amount'))['total'] or 0

    if total_spent == 0:
        ratio = 0.0
    else:
        category_spent = Ledger.objects.filter(
            user=user,
            date=target_date,
            category=base_challenge.category,
        ).aggregate(total=Sum('amount'))['total'] or 0
        ratio = category_spent / total_spent

    base_score, bonus_restricted = _calc_base_score(ratio)

    # 연속 달성/미달성 보너스
    streak_bonus = 0 if bonus_restricted else _calc_streak_bonus(member, target_date)

    raw_score = base_score + streak_bonus

    # 하루 최대 +10점 캡 (음수는 제한 없음)
    if raw_score > 10:
        raw_score = 10

    # 감쇠 공식 적용 (양수일 때만)
    current_score = member.group_score
    if raw_score > 0:
        actual_delta = raw_score * (100 - current_score) / 30
    else:
        actual_delta = float(raw_score)

    # 0~100 클램핑
    new_score = current_score + actual_delta
    new_score = max(0.0, min(100.0, new_score))
    actual_delta = new_score - current_score

    if actual_delta == 0:
        return

    reason = 'daily_achieve' if actual_delta > 0 else 'daily_penalty'
    _apply_score(member, actual_delta, reason)


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
        check_and_update_group_score(user, member.group, target_date)


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