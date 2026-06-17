import json
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from accounts.models import UserScore
from accounts.services import record_achievement
from .models import Ledger
from groups.services import record_group_daily 

def first(request):
    return render(request, 'ledger/first.html')


@login_required(login_url='accounts:login')
def main(request):
    user = request.user
    today = date.today()

    total_spent = Ledger.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0

    score_obj, _ = UserScore.objects.get_or_create(
        user=user,
        defaults={'score': 60}
    )
    score = score_obj.score

    spending_dates = {
        str(d): True
        for d in Ledger.objects.filter(
            user=user,
        ).values_list('date', flat=True).distinct()
    }

    context = {
        'user': user,
        'total_spent': total_spent,
        'score': score,
        'spending_dates_json': json.dumps(spending_dates, default=str),
    }

    return render(request, 'ledger/main.html', context)


@login_required(login_url='accounts:login')
def detail(request, year, month, day):
    user = request.user
    spent_date = date(year, month, day)

    if request.method == 'POST':
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        memo = request.POST.get('memo')

        if amount and int(amount) > 0:
            Ledger.objects.create(
                user=user,
                date=spent_date,
                category=category,
                amount=int(amount),
                memo=memo,
            )

        total_spent = Ledger.objects.filter(
            user=user,
            date=spent_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        record_achievement(user, spent_date, total_spent)
        record_group_daily(user, spent_date)

        return redirect('ledger:detail', year=year, month=month, day=day)

    ledgers = Ledger.objects.filter(user=user, date=spent_date)

    total_spent = ledgers.aggregate(
        total=Sum('amount')
    )['total'] or 0

    category_totals = {}
    for choice in Ledger.CATEGORY_CHOICES:
        key = choice[0]
        label = choice[1]
        total = ledgers.filter(category=key).aggregate(
            total=Sum('amount')
        )['total'] or 0
        category_totals[key] = {'label': label, 'total': total}

    if user.daily_budget > 0:
        ratio_value = total_spent / user.daily_budget
    else:
        ratio_value = 0

    ratio = round(ratio_value * 100, 1)

    top_category = None
    top_amount = 0

    for item in category_totals.values():
        if item['total'] > top_amount:
            top_amount = item['total']
            top_category = item['label']

    if ratio_value < 0.5:
        danger = "보통"
        warning = "현재 지출이 안정적입니다. 지금처럼 소비를 유지해도 좋습니다."
    elif ratio_value < 0.7:
        danger = "주의"
        warning = "목표 금액의 50%를 넘었습니다. 남은 소비를 조절해보세요."
    else:
        danger = "위험"
        warning = "목표 금액의 70% 이상을 사용했습니다. 오늘은 꼭 필요한 소비만 하는 것이 좋습니다."

    if top_category == "카페/간식":
        category_tip = "☕ 카페 지출이 많습니다. 텀블러 할인이나 집커피를 활용해보세요."
    elif top_category == "쇼핑":
        category_tip = "🛍️ 쇼핑 지출이 많습니다. 필요한 물건인지 한 번 더 확인해보세요."
    elif top_category == "구독":
        category_tip = "📺 사용하지 않는 구독 서비스가 있는지 확인해보세요."
    elif top_category == "문화생활":
        category_tip = "🎬 문화생활 지출이 높습니다. 이번 주 예산을 확인해보세요."
    elif top_category == "식비":
        category_tip = "🍔 식비 지출이 가장 높습니다. 배달 횟수를 줄여보는 건 어떨까요?"
    elif top_category == "교통비":
        category_tip = "🚌 교통비 지출이 많습니다. 도보나 대중교통 환승을 활용해보세요."
    elif top_category == "여가비":
        category_tip = "🎮 여가비 지출이 많습니다. 남은 예산을 확인해보세요."
    else:
        category_tip = "💰 현재 가장 높은 소비 항목을 확인해보세요."

    context = {
        'user': user,
        'spent_date': spent_date,
        'ledgers': ledgers,
        'total_spent': total_spent,
        'category_totals': category_totals,
        'daily_budget': user.daily_budget,
        'ratio': ratio,
        'danger': danger,
        'warning': warning,
        'category_tip': category_tip,
        'category_choices': Ledger.CATEGORY_CHOICES, 
    }

    return render(request, 'ledger/detail.html', context)