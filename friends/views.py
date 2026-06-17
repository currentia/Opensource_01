from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date

from .models import FriendRequest
from accounts.models import User, UserScore, DailyAchievement


def get_score(user):
    """유저의 점수를 안전하게 조회 (없으면 60점 반환)"""
    score_obj, created = UserScore.objects.get_or_create(user=user, defaults={'score': 60})
    return score_obj.score


def get_today_achieved(user):
    """오늘 달성 여부 반환 (기록 없으면 None)"""
    try:
        record = DailyAchievement.objects.get(user=user, date=date.today())
        return record.achieved
    except DailyAchievement.DoesNotExist:
        return None


@login_required(login_url='accounts:login')
def friend_main(request):
    me = request.user

    # ── 수락된 친구 목록 ──
    sent_accepted     = FriendRequest.objects.filter(from_user=me, status='accepted').select_related('to_user')
    received_accepted = FriendRequest.objects.filter(to_user=me,   status='accepted').select_related('from_user')

    friends = []
    for req in sent_accepted:
        friends.append(req.to_user)
    for req in received_accepted:
        friends.append(req.from_user)

    # 친구 목록에 점수 + 오늘 달성 여부 추가
    friends_with_score = [
        {
            'user':     friend,
            'score':    get_score(friend),
            'achieved': get_today_achieved(friend),
        }
        for friend in friends
    ]

    # 나의 점수
    my_score = get_score(me)

    # 나 포함 랭킹 (점수 내림차순)
    ranking = [{'user': me, 'score': my_score}] + friends_with_score
    ranking.sort(key=lambda x: x['score'], reverse=True)

    # ── 받은 친구 요청 (대기중) ──
    pending_requests = FriendRequest.objects.filter(
        to_user=me, status='pending'
    ).select_related('from_user')

    # ── 내가 보낸 요청 (대기중) ──
    sent_pending = FriendRequest.objects.filter(
        from_user=me, status='pending'
    ).values_list('to_user_id', flat=True)

    context = {
        'friends_with_score': friends_with_score,
        'ranking':            ranking,
        'pending_requests':   pending_requests,
        'sent_pending':       list(sent_pending),
        'my_score':           my_score,
    }

    return render(request, 'friends/friend.html', context)


@login_required(login_url='accounts:login')
def send_request(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        me       = request.user

        if username == me.username: # 자기 자신에게 친구 요청 방지
            messages.error(request, '자기 자신에게는 요청을 보낼 수 없습니다.')
            return redirect('friends:friend_main')

        try:
            to_user = User.objects.get(username=username)
        except User.DoesNotExist: # 아이디 존재 x
            messages.error(request, '존재하지 않는 아이디입니다.')
            return redirect('friends:friend_main')

        already = FriendRequest.objects.filter(
            from_user=me, to_user=to_user
        ).exists() or FriendRequest.objects.filter(
            from_user=to_user, to_user=me
        ).exists()

        if already:
            messages.warning(request, '친구 요청을 보낸 상태이거나 현재 친구인 상태입니다.')
        else:
            FriendRequest.objects.create(from_user=me, to_user=to_user)
            messages.success(request, f'{to_user.name}님에게 친구 요청을 보냈습니다.')

    # 1. 자기 자신에게 요청? ──> redirect 
    # 2. 존재하지 않는 유저? ──> 에러 메시지 렌더링
    # 3. 이미 요청 존재?     ──> 무시 (중복 방지)

    return redirect('friends:friend_main')

@login_required(login_url='accounts:login')
def accept_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    friend_request.status = 'accepted'
    friend_request.save()
    return redirect('friends:friend_main')


@login_required(login_url='accounts:login')
def reject_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    friend_request.status = 'rejected'
    friend_request.save()
    return redirect('friends:friend_main')