import json
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from accounts.models import UserScore
from accounts.services import record_achievement
from .models import Ledger


def first(request):
    return render(request, 'ledger/first.html')


@login_required(login_url='accounts:login')
def main(request):
    user  = request.user
    today = date.today()

    # 이번 달 지출 합계
    total_spent = Ledger.objects.filter( # filter() -> 인번 연도, 이번 달 데이터만 필터링
        user=user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0 # 필터된 행의 amount를 합산, 이후 ['total']로 aggregate 결과 딕셔너리에서 값 추출
                                                   # 데이터가 없으면 None이 반환되므로 0으로 대체

    # 현재 점수
    score_obj, _ = UserScore.objects.get_or_create( # get_or_create() 는 조회 + 없으면 생성
        user=user, defaults={'score': 60}
    )
    score = score_obj.score

    # 지출 내역이 있는 날짜 목록 (캘린더 점 표시용)
    spending_dates = {
        str(d): True # date 객체를 문자열로 변환해서 딕셔너리 생성
        for d in Ledger.objects.filter(
            user=user,
            date__year=today.year,
            date__month=today.month
        ).values_list('date', flat=True).distinct() # distinct() 중복 날짜 제거
    }

    context = {
        'user':                user,
        'total_spent':         total_spent,
        'score':               score,
        'spending_dates_json': json.dumps(spending_dates, default=str),
    }

    return render(request, 'ledger/main.html', context)


@login_required(login_url='accounts:login')
def detail(request, year, month, day):
    user        = request.user
    spent_date  = date(year, month, day) # /ledger/2026/5/26/ 형태라면 year=2026, month=5, day=26이 자동으로 들어옴

    if request.method == 'POST':
        # 기존 해당 날짜 지출 전체 삭제 후 재저장
        Ledger.objects.filter(user=user, date=spent_date).delete()

        categories = request.POST.getlist('category') # 복수 데이터 수집
        amounts    = request.POST.getlist('amount')
        memos      = request.POST.getlist('memo')

        for category, amount, memo in zip(categories, amounts, memos): # 순서대로 묶기
            if amount and int(amount) > 0:
                Ledger.objects.create( # 유효한 것만 저장
                    user     = user,
                    date     = spent_date,
                    category = category,
                    amount   = int(amount),
                    memo     = memo,
                )

        # 총 지출 계산 후 달성 여부 기록 및 점수 업데이트
        total_spent = Ledger.objects.filter(
            user=user, date=spent_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        record_achievement(user, spent_date, total_spent) # 저장 후 총 지출을 계산하여 record_achievement 서비스 함수로 넘김

        return redirect('ledger:detail', year=year, month=month, day=day)

    # GET: 해당 날짜 지출 내역 조회
    ledgers = Ledger.objects.filter(user=user, date=spent_date)

    total_spent = ledgers.aggregate(
        total=Sum('amount')
    )['total'] or 0

    # 카테고리별 합계
    category_totals = {}
    for choice in Ledger.CATEGORY_CHOICES: # CATEGORY_CHOICES는 Ledger 모델에 정의된 카테고리 목록
        key   = choice[0]
        label = choice[1]
        total = ledgers.filter(category=key).aggregate(
            total=Sum('amount')
        )['total'] or 0
        category_totals[key] = {'label': label, 'total': total}

    context = {
        'user':             user,
        'spent_date':       spent_date,
        'ledgers':          ledgers,
        'total_spent':      total_spent,
        'category_totals':  category_totals,
        'daily_budget':     user.daily_budget,
    }

    return render(request, 'ledger/detail.html', context)
