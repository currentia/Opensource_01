from datetime import date, timedelta
from .models import UserScore, DailyAchievement


# ──────────────────────────────────────────
# 상수 정의
# ──────────────────────────────────────────
BASE_SCORE      = 60
SCORE_MIN       = 0
SCORE_MAX       = 100
DAILY_SCORE_CAP = 10   # 하루 최대 획득 점수


# ──────────────────────────────────────────
# ① 기본 점수 산출 (사용률 구간별)
# ──────────────────────────────────────────
def _calc_base_score(usage_rate: float) -> tuple[int, bool]:
    """
    usage_rate : 실제지출 / 일일예산 (0.0 ~ 그 이상)
    반환값     : (기본점수, 보너스_허용_여부)

    구간 정의
    0%  +1     보너스 제한      
    0% 초과 ~ 30%   +1              
    30% 초과 ~ 50%  +3             
    50% 초과 ~ 80%  +4      
    80% 초과 ~100%  +2            
    100% 초과 ~120% 0   보너스 제한           
    120% 초과   -2  보너스 제한            
    """
    if usage_rate == 0.0:
        return 1, False          # 0% 사용 → 보너스 제한
    elif usage_rate <= 0.30:
        return 1, True
    elif usage_rate <= 0.50:
        return 3, True
    elif usage_rate <= 0.80:
        return 4, True           # 이상적인 절약 구간
    elif usage_rate <= 1.00:
        return 2, True
    elif usage_rate <= 1.20:
        return 0, False
    else:
        return -2, False


# ──────────────────────────────────────────
# ② 연속 달성 보너스 산출
# ──────────────────────────────────────────
def _calc_streak_bonus(user) -> int:
    """
    오늘 기준 역순으로 연속 달성일 계산
    3일 연속 → +1점
    7일 연속 → +2점  (3일 보너스와 중복 적용 안 함, 더 높은 쪽만)
    """
    today  = date.today()
    streak = 0

    for i in range(7):
        d = today - timedelta(days=i)
        try:
            record = DailyAchievement.objects.get(user=user, date=d)
            if record.achieved:
                streak += 1
            else:
                break
        except DailyAchievement.DoesNotExist:
            break

    if streak >= 7:
        return 2
    elif streak >= 3:
        return 1
    return 0


# ──────────────────────────────────────────
# ③ 지난주 평균 대비 보너스 산출
# ──────────────────────────────────────────
def _calc_weekly_comparison_bonus(user, today_spent: float) -> int:
    """
    지난주(7일 전 ~ 1일 전) 일평균 지출과 오늘 지출 비교
    오늘 지출 < 지난주 평균 → +1점
    오늘 지출 > 지난주 평균 → -3점
    데이터 없으면            →  0점
    """
    today = date.today()
    last_week_dates = [today - timedelta(days=i) for i in range(1, 8)]

    records = DailyAchievement.objects.filter(
        user=user,
        date__in=last_week_dates
    ).values_list('daily_spent', flat=True)

    if not records:
        return 0

    last_week_avg = sum(records) / len(records)

    if today_spent < last_week_avg:
        return 1
    elif today_spent > last_week_avg:
        return -3
    return 0


# ──────────────────────────────────────────
# ④ 감쇠 공식 적용
# ──────────────────────────────────────────
def _apply_diminishing_return(raw_score: int, current_score: float) -> float:
    """
    점수가 높을수록 실제 상승폭을 줄이는 감쇠 공식
    실제 상승 점수 = raw_score × (100 - 현재점수) / 40

    예시)
    raw_score=+9, 현재 60점 → 9 × 40/40 = +9.0
    raw_score=+9, 현재 90점 → 9 × 10/40 = +2.25
    raw_score=+9, 현재 98점 → 9 × 2/40  = +0.45

    ※ 마이너스 점수는 감쇠 적용 안 함 (패널티는 그대로)
    """
    if raw_score <= 0:
        return float(raw_score)
    return raw_score * (100 - current_score) / 40


# ──────────────────────────────────────────
# 메인 진입점
# ──────────────────────────────────────────
def record_achievement(user, spent_date, total_spent: float):
    """
    지출 입력/수정 시 호출되는 메인 함수

    처리 순서
    1. 사용률 계산
    2. 달성 여부 판정 → DailyAchievement 저장
    3. 점수 계산 → UserScore 업데이트
    """
    daily_budget = float(user.daily_budget)

    # 예산이 0이면 사용률 계산 불가 → 처리 중단
    if daily_budget <= 0:
        return

    usage_rate  = total_spent / daily_budget
    achieved    = usage_rate <= 1.0

    # DailyAchievement 저장 (daily_spent 필드 필요)
    DailyAchievement.objects.update_or_create(
        user=user,
        date=spent_date,
        defaults={
            'achieved':    achieved,
            'daily_spent': total_spent,
        }
    )

    # 점수 업데이트
    _update_score(user, usage_rate, total_spent)


def _update_score(user, usage_rate: float, today_spent: float):
    """
    점수 계산 파이프라인
    ① 기본 점수
    ② 보너스 점수 (보너스 허용 시)
    ③ 하루 최대 +10 캡
    ④ 감쇠 공식
    ⑤ 0~100 클램핑 후 저장
    """
    score_obj, _ = UserScore.objects.get_or_create(
        user=user,
        defaults={'score': BASE_SCORE}
    )
    current_score = float(score_obj.score)

    # ① 기본 점수
    base_score, bonus_allowed = _calc_base_score(usage_rate)
    today_score = base_score

    # ② 보너스 점수 (0% 사용이 아닐 때만)
    if bonus_allowed:
        today_score += _calc_streak_bonus(user)
        today_score += _calc_weekly_comparison_bonus(user, today_spent)

    # ③ 하루 최대 +10 캡 (마이너스는 그대로)
    if today_score > DAILY_SCORE_CAP:
        today_score = DAILY_SCORE_CAP

    # ④ 감쇠 공식 적용
    actual_delta = _apply_diminishing_return(today_score, current_score)

    # ⑤ 0~100 클램핑 후 저장
    new_score = current_score + actual_delta
    score_obj.score = max(SCORE_MIN, min(SCORE_MAX, new_score))
    score_obj.save()


# ──────────────────────────────────────────
# 조회용 유틸
# ──────────────────────────────────────────
def get_streak_info(user) -> dict:
    """
    현재 연속 달성/미달성 일수 반환 (템플릿 표시용)
    """
    today           = date.today()
    streak_achieved = 0
    streak_failed   = 0

    for i in range(30):   # 최대 30일까지 탐색
        d = today - timedelta(days=i)
        try:
            record = DailyAchievement.objects.get(user=user, date=d)
            if i == 0:
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