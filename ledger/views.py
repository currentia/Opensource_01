import json
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from accounts.models import UserScore
from accounts.services import record_achievement
from .models import Ledger


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
            date__year=today.year,
            date__month=today.month
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
        categories = request.POST.getlist('category')
        amounts = request.POST.getlist('amount')
        memos = request.POST.getlist('memo')

        for category, amount, memo in zip(categories, amounts, memos):
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
        if top_category:
            warning = f"목표 금액의 50%를 넘었습니다. 오늘은 {top_category} 지출이 가장 많으니 남은 소비를 조절해보세요."
        else:
            warning = "목표 금액의 50%를 넘었습니다. 남은 소비를 조금 줄여보세요."
    else:
        danger = "위험"
        if top_category:
            warning = f"목표 금액의 70% 이상을 사용했습니다. 특히 {top_category} 지출이 많으므로 오늘은 꼭 필요한 소비만 하는 것이 좋습니다."
        else:
            warning = "목표 금액의 70% 이상을 사용했습니다. 오늘은 꼭 필요한 소비만 하는 것이 좋습니다."

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
    }

    return render(request, 'ledger/detail.html', context)