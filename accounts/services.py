from datetime import date, timedelta
from .models import UserScore, DailyAchievement


def record_achievement(user, spent_date, total_spent):
    """
    하루 지출 저장 시 달성 여부를 기록하고 점수를 업데이트
    - total_spent : 해당 날짜의 총 지출 금액
    - user.daily_budget : 일 목표 금액
    """
    achieved = total_spent <= user.daily_budget

    # 달성 이력 저장 (이미 있으면 업데이트)
    DailyAchievement.objects.update_or_create(
        user=user,
        date=spent_date,
        defaults={'achieved': achieved}
    )

    # 점수 업데이트 여부 확인
    check_and_update_score(user)


def check_and_update_score(user):
    """
    최근 10일 연속 달성/미달성 여부를 확인하고 점수를 업데이트, 추후 수정 필요
    - 10일 연속 달성  → +1점
    - 10일 연속 미달  → -1점
    - 그 외           → 변동 없음
    """
    today = date.today()

    # 최근 10일 날짜 목록 (오늘 포함)
    dates = [today - timedelta(days=i) for i in range(10)]

    # 최근 10일 달성 기록 조회
    records = DailyAchievement.objects.filter(
        user=user,
        date__in=dates
    ).values_list('date', 'achieved')

    record_dict = {r[0]: r[1] for r in records}

    # 10일치 데이터가 없으면 점수 변동 없음
    if len(record_dict) < 10:
        return

    score_obj, _ = UserScore.objects.get_or_create(
        user=user,
        defaults={'score': 60}
    )

    # 10일 연속 달성
    if all(record_dict.get(d) == True for d in dates):
        score_obj.score += 1
        score_obj.save()

    # 10일 연속 미달성
    elif all(record_dict.get(d) == False for d in dates):
        score_obj.score -= 1
        score_obj.save()


def get_streak_info(user):
    """
    현재 연속 달성/미달성 일수 반환
    - 오늘부터 역순으로 연속된 날짜 카운트
    """
    today = date.today()
    streak_achieved = 0
    streak_failed   = 0

    for i in range(10):
        d = today - timedelta(days=i)
        try:
            record = DailyAchievement.objects.get(user=user, date=d)
            if i == 0:
                # 오늘 기준으로 연속 방향 결정
                if record.achieved:
                    streak_achieved += 1
                else:
                    streak_failed += 1
            else:
                if record.achieved and streak_achieved > 0:
                    streak_achieved += 1
                elif not record.achieved and streak_failed > 0:
                    streak_failed += 1
                else:
                    break
        except DailyAchievement.DoesNotExist:
            break

    return {
        'streak_achieved': streak_achieved,
        'streak_failed':   streak_failed,
    }
