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

        Ledger.objects.filter(
            user=user,
            date=spent_date
        ).delete()

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

        record_achievement(
            user,
            spent_date,
            total_spent
        )

        return redirect(
            'ledger:detail',
            year=year,
            month=month,
            day=day
        )

    ledgers = Ledger.objects.filter(
        user=user,
        date=spent_date
    )

    total_spent = ledgers.aggregate(
        total=Sum('amount')
    )['total'] or 0

    category_totals = {}

    for choice in Ledger.CATEGORY_CHOICES:

        key = choice[0]
        label = choice[1]

        total = ledgers.filter(
            category=key
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0

        category_totals[key] = {
            'label': label,
            'total': total
        }

    # 소비 경보 기능 (김지안 작업)
    if user.daily_budget and user.daily_budget > 0:

        spending_ratio = total_spent / user.daily_budget

        if spending_ratio >= 0.7:
            warning_message = "지출이 목표 금액의 70%를 넘었습니다. 소비를 줄이는 것이 좋습니다."

        elif spending_ratio >= 0.5:
            warning_message = "지출이 목표 금액의 50%를 넘었습니다. 지출에 주의하세요."

        else:
            warning_message = "아직 지출 상태가 양호합니다."

    else:
        spending_ratio = 0
        warning_message = "목표 금액이 설정되지 않았습니다."

    context = {
        'user': user,
        'spent_date': spent_date,
        'ledgers': ledgers,
        'total_spent': total_spent,
        'category_totals': category_totals,
        'daily_budget': user.daily_budget,
        'warning_message': warning_message,
        'spending_ratio': spending_ratio,
    }

    return render(
        request,
        'ledger/detail.html',
        context
    )