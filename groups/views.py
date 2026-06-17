from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.utils import timezone

from friends.models import FriendRequest
from ledger.models import Ledger
from .models import (
    Group,
    GroupMember,
    GroupInvite,
    Challenge,
    CustomChallenge,
    Feedback,
    CATEGORY_CHOICES,
)
from .services import (
    get_group_ranking,
    get_group_streak_info,
    apply_challenge_score,
)

User = get_user_model()


# ──────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────

def _is_friend(user, target):
    """두 유저가 친구 관계인지 확인 (accepted 상태만)"""
    return FriendRequest.objects.filter(
        Q(from_user=user, to_user=target) |
        Q(from_user=target, to_user=user),
        status='accepted',
    ).exists()


def _is_member(group, user):
    """해당 유저가 모임 멤버인지 확인"""
    return GroupMember.objects.filter(group=group, user=user).exists()


# ──────────────────────────────────────────────
# 1. 모임 목록
# ──────────────────────────────────────────────

@login_required
def group_list(request):
    """
    내가 속한 모임 목록 + 받은 초대 목록 표시
    """
    my_groups = Group.objects.filter(
        members__user=request.user
    ).select_related('owner').prefetch_related('members')

    pending_invites = GroupInvite.objects.filter(
        to_user=request.user,
        status='pending',
    ).select_related('group', 'from_user')

    return render(request, 'groups/list.html', {
        'my_groups':       my_groups,
        'pending_invites': pending_invites,
    })


# ──────────────────────────────────────────────
# 2. 모임 생성
# ──────────────────────────────────────────────

@login_required
def group_create(request):
    """
    모임 생성 + 기본 챌린지 설정
    POST 파라미터:
        - name        : 모임 이름
        - end_date    : 종료일
        - category    : 기본 챌린지 카테고리
        - ratio_limit : 기본 챌린지 비율 기준 (0.0 ~ 1.0)
    """
    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        end_date    = request.POST.get('end_date')
        category    = request.POST.get('category')
        ratio_limit = request.POST.get('ratio_limit')

        # 유효성 검사
        if not all([name, end_date, category, ratio_limit]):
            return render(request, 'groups/create.html', {
                'error':            '모든 항목을 입력해 주세요.',
                'category_choices': CATEGORY_CHOICES,
            })

        try:
            ratio_limit = float(ratio_limit)
            if not (0.0 < ratio_limit <= 1.0):
                raise ValueError
        except ValueError:
            return render(request, 'groups/create.html', {
                'error':            '비율은 0 초과 1 이하의 숫자로 입력해 주세요.',
                'category_choices': CATEGORY_CHOICES,
            })

        # 모임 생성
        group = Group.objects.create(
            name=name,
            owner=request.user,
            end_date=end_date,
        )

        # 모임장을 멤버로 자동 등록
        GroupMember.objects.create(group=group, user=request.user)

        # 기본 챌린지 생성
        Challenge.objects.create(
            group=group,
            category=category,
            ratio_limit=ratio_limit,
        )

        return redirect('groups:group_detail', group_id=group.pk)

    return render(request, 'groups/create.html', {
        'category_choices': CATEGORY_CHOICES,
    })


# ──────────────────────────────────────────────
# 3. 모임 상세
# ──────────────────────────────────────────────

@login_required
def group_detail(request, group_id):
    """
    모임 상세 페이지
    - 멤버 목록 + 점수 랭킹
    - 기본/커스텀 챌린지 목록
    - D-day
    - 내 연속 달성 정보
    """
    group = get_object_or_404(Group, pk=group_id)

    # 멤버가 아니면 접근 차단
    if not _is_member(group, request.user):
        return redirect('groups:group_list')

    today   = timezone.now().date()
    d_day   = (group.end_date - today).days

    ranking           = get_group_ranking(group)
    streak_info       = get_group_streak_info(request.user, group)
    challenges        = group.challenges.all()
    custom_challenges = group.custom_challenges.all()
    is_owner          = (group.owner == request.user)

    # 초대 가능한 친구 목록 (모임장만 사용)
    if is_owner:
        from friends.models import FriendRequest
        accepted = FriendRequest.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status='accepted',
        ).select_related('from_user', 'to_user')

        friends = []
        for req in accepted:
            friend = req.to_user if req.from_user == request.user else req.from_user
            if not _is_member(group, friend):
                friends.append(friend)
    else:
        friends = []

    return render(request, 'groups/detail.html', {
        'group':             group,
        'd_day':             d_day,
        'today':             today,
        'ranking':           ranking,
        'streak_info':       streak_info,
        'challenges':        challenges,
        'custom_challenges': custom_challenges,
        'is_owner':          is_owner,
        'invitable_friends': friends,
        'category_choices':  CATEGORY_CHOICES,
    })


# ──────────────────────────────────────────────
# 4. 모임 초대
# ──────────────────────────────────────────────

@login_required
def group_invite(request, group_id):
    """
    친구를 모임에 초대
    POST 파라미터:
        - to_user_id : 초대할 유저 pk
    """
    group = get_object_or_404(Group, pk=group_id)

    # 모임장만 초대 가능
    if group.owner != request.user:
        return redirect('groups:group_detail', group_id=group_id)

    if request.method == 'POST':
        to_user_id = request.POST.get('to_user_id')
        to_user    = get_object_or_404(User, pk=to_user_id)

        # 친구 여부 검증
        if not _is_friend(request.user, to_user):
            return redirect('groups:group_detail', group_id=group_id)

        # 최대 인원 검증
        current_count = GroupMember.objects.filter(group=group).count()
        if current_count >= group.max_members:
            return redirect('groups:group_detail', group_id=group_id)

        # 이미 멤버인지 확인
        if _is_member(group, to_user):
            return redirect('groups:group_detail', group_id=group_id)

        # 초대 생성 (이미 pending 초대가 있으면 무시)
        GroupInvite.objects.get_or_create(
            group=group,
            to_user=to_user,
            defaults={'from_user': request.user, 'status': 'pending'},
        )

    return redirect('groups:group_detail', group_id=group_id)


# ──────────────────────────────────────────────
# 5. 초대 수락 / 거절
# ──────────────────────────────────────────────

@login_required
def group_invite_respond(request, invite_id, action):
    """
    초대 수락 or 거절
    action : 'accept' or 'reject'
    """
    invite = get_object_or_404(GroupInvite, pk=invite_id, to_user=request.user)

    if invite.status != 'pending':
        return redirect('groups:group_list')

    if action == 'accept':
        # 최대 인원 재검증 (수락 시점 기준)
        current_count = GroupMember.objects.filter(group=invite.group).count()
        if current_count >= invite.group.max_members:
            invite.status = 'rejected'
            invite.save(update_fields=['status'])
            return redirect('groups:group_list')

        invite.status = 'accepted'
        invite.save(update_fields=['status'])
        GroupMember.objects.get_or_create(group=invite.group, user=request.user)

    elif action == 'reject':
        invite.status = 'rejected'
        invite.save(update_fields=['status'])

    return redirect('groups:group_list')


# ──────────────────────────────────────────────
# 6. 커스텀 챌린지 생성
# ──────────────────────────────────────────────

@login_required
def custom_challenge_create(request, group_id):
    """
    커스텀 챌린지 등록
    POST 파라미터:
        - amount_limit : 하루 지출 한도 금액
        - bonus_score  : 달성 시 보너스 점수 (1~5)
        - description  : 설명 (선택)
    카테고리: 모임의 기본 챌린지 카테고리로 자동 고정
    expires_date: 등록 당일로 자동 설정 (당일 23:59까지 유효)
    """
    group = get_object_or_404(Group, pk=group_id)

    # 모임장만 커스텀 챌린지 생성 가능
    if group.owner != request.user:
        return redirect('groups:group_detail', group_id=group_id)

    if request.method == 'POST':
        amount_limit = request.POST.get('amount_limit')
        bonus_score  = request.POST.get('bonus_score', 1)
        description  = request.POST.get('description', '').strip()

        # 기본 챌린지 카테고리 자동 설정
        base_challenge = group.challenges.first()
        if not base_challenge:
            return redirect('groups:group_detail', group_id=group_id)
        category = base_challenge.category

        try:
            amount_limit = int(amount_limit)
            if amount_limit <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return redirect('groups:group_detail', group_id=group_id)

        try:
            bonus_score = int(bonus_score)
            if not (1 <= bonus_score <= 5):
                raise ValueError
        except (ValueError, TypeError):
            return redirect('groups:group_detail', group_id=group_id)

        CustomChallenge.objects.create(
            group=group,
            created_by=request.user,
            category=category,
            amount_limit=amount_limit,
            bonus_score=bonus_score,
            expires_date=timezone.now().date(),
            description=description,
        )

    return redirect('groups:group_detail', group_id=group_id)


# ──────────────────────────────────────────────
# 6-1. 커스텀 챌린지 삭제 (모임장 전용)
# ──────────────────────────────────────────────

@login_required
def custom_challenge_delete(request, group_id, challenge_id):
    """
    커스텀 챌린지 삭제 - 모임장만 가능
    """
    group     = get_object_or_404(Group, pk=group_id)
    challenge = get_object_or_404(CustomChallenge, pk=challenge_id, group=group)

    if group.owner != request.user:
        return redirect('groups:group_detail', group_id=group_id)

    if request.method == 'POST':
        challenge.delete()

    return redirect('groups:group_detail', group_id=group_id)


# ──────────────────────────────────────────────
# 7. 피드백 작성
# ──────────────────────────────────────────────

@login_required
def feedback_create(request, group_id):
    """
    member_ledger 페이지에서 댓글 저장
    POST 파라미터:
        - target_user_id : 지출 게시글 주인 pk
        - ledger_date    : 게시글 날짜
        - content        : 댓글 내용
    """
    group = get_object_or_404(Group, pk=group_id)

    if not _is_member(group, request.user):
        return redirect('groups:group_list')

    if request.method == 'POST':
        target_user_id = request.POST.get('target_user_id')
        ledger_date    = request.POST.get('ledger_date')
        content        = request.POST.get('content', '').strip()

        target_user = get_object_or_404(User, pk=target_user_id)

        if not _is_member(group, target_user):
            return redirect('groups:group_detail', group_id=group_id)

        if content:
            Feedback.objects.create(
                group=group,
                from_user=request.user,
                target_user=target_user,
                ledger_date=ledger_date,
                content=content,
            )
            return redirect(
                'groups:member_ledger',
                group_id=group_id,
                user_id=target_user.pk,
                ledger_date=ledger_date,
            )

    return redirect('groups:group_detail', group_id=group_id)


# ──────────────────────────────────────────────
# 7-1. 멤버 하루 지출 조회 + 피드백 작성
# ──────────────────────────────────────────────

@login_required
def member_ledger(request, group_id, user_id, ledger_date):
    """
    특정 멤버의 하루 지출 게시글
    - 카테고리별 합산 표시
    - 모임 멤버 누구나 댓글(피드백) 열람/작성 가능
    """
    group       = get_object_or_404(Group, pk=group_id)
    target_user = get_object_or_404(User, pk=user_id)

    if not _is_member(group, request.user):
        return redirect('groups:group_list')

    if not _is_member(group, target_user):
        return redirect('groups:group_detail', group_id=group_id)

    # CATEGORY_CHOICES에서 자동 생성 → 카테고리 추가 시 자동 반영
    CATEGORY_LABELS = dict(CATEGORY_CHOICES)

    raw = Ledger.objects.filter(
        user=target_user,
        date=ledger_date,
    ).values('category').annotate(total=Sum('amount'))

    category_summary = [
        {
            'category': row['category'],
            'label':    CATEGORY_LABELS.get(row['category'], row['category']),
            'total':    row['total'],
        }
        for row in raw
    ]

    total_spent = sum(row['total'] for row in category_summary)

    feedbacks = Feedback.objects.filter(
        group=group,
        target_user=target_user,
        ledger_date=ledger_date,
    ).select_related('from_user').order_by('created_at')

    return render(request, 'groups/member_ledger.html', {
        'group':            group,
        'target_user':      target_user,
        'ledger_date':      ledger_date,
        'category_summary': category_summary,
        'total_spent':      total_spent,
        'feedbacks':        feedbacks,
        'is_own':           target_user == request.user,
    })


# ──────────────────────────────────────────────
# 8. 모임 종료 (모임장 전용)
# ──────────────────────────────────────────────

@login_required
def group_close(request, group_id):
    """
    모임 종료 시 챌린지 보너스/패널티 점수 최종 반영
    - 모임장만 수동 종료 가능
    """
    group = get_object_or_404(Group, pk=group_id)

    if group.owner != request.user:
        return redirect('groups:group_detail', group_id=group_id)

    if request.method == 'POST':
        members = GroupMember.objects.filter(group=group).select_related('user')
        for member in members:
            apply_challenge_score(member.user, group)

        group.delete()
        return redirect('groups:group_list')

    return render(request, 'groups/close_confirm.html', {'group': group})