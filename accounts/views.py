from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

from .models import User, UserScore


# ── 로그인 ──
def login_view(request):
    if request.user.is_authenticated: # 이미 로그인한 상태라면 main.html로 리다이렉트
        return redirect('ledger:main')

    if request.method == 'POST': # 로그인 버튼 클릭 시
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid(): # 폼이 유효하면
            user = form.get_user()
            login(request, user)
            return redirect('ledger:main') # main.html로 리다이렉트
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


# ── 로그아웃 ──
def logout_view(request): # 세션 파괴 이후 first.html로 이동
    logout(request)
    return redirect('ledger:first')


# ── 회원가입 ──
def signup_view(request):
    if request.user.is_authenticated: # 이미 로그인한 사용자는 main.html로 이동
        return redirect('ledger:main')

    if request.method == 'POST':
        # 폼 데이터 수집 request.POST.get('키', '기본값') : HTML 폼에서 넘어온 데이터를 꺼냄
        username     = request.POST.get('username', '').strip()
        password1    = request.POST.get('password1', '')
        password2    = request.POST.get('password2', '')
        name         = request.POST.get('name', '').strip()
        birth        = request.POST.get('birth', '')
        daily_budget = request.POST.get('daily_budget', '0')

        errors    = []
        form_data = {
            'username':     username,
            'name':         name,
            'birth':        birth,
            'daily_budget': daily_budget,
        }

        # ── 서버 측 유효성 검사 ──
        if len(username) < 4:
            errors.append('아이디는 4자 이상이어야 합니다.')

        if User.objects.filter(username=username).exists():
            errors.append('이미 사용 중인 아이디입니다.')

        if len(password1) < 8:
            errors.append('비밀번호는 8자 이상이어야 합니다.')

        if password1 != password2:
            errors.append('비밀번호가 일치하지 않습니다.')

        if not name:
            errors.append('이름을 입력해 주세요.')

        if not birth:
            errors.append('생년월일을 입력해 주세요.')

        try:
            daily_budget = int(daily_budget)
            if daily_budget <= 0:
                errors.append('올바른 금액을 입력해 주세요.')
        except ValueError:
            errors.append('올바른 금액을 입력해 주세요.')

        # 에러가 있으면 다시 회원가입 폼으로
        if errors:
            return render(request, 'accounts/signup.html', {
                'errors':    errors,
                'form_data': form_data,
            })

        # ── 회원 생성 ──
        user = User.objects.create_user( # create_user() : 일반 create()와 달리 비밀번호를 자동으로 해싱해서 저장
            username     = username,
            password     = password1,
            name         = name,
            birth        = birth,
            daily_budget = daily_budget,
        )

        # 점수 테이블 초기화 (기본 60점)
        UserScore.objects.create(user=user, score=60) # 회원가입과 동시에 점수 레코드도 함께 생성

        # 가입 후 자동 로그인
        login(request, user)
        return redirect('ledger:main')

    return render(request, 'accounts/signup.html')
