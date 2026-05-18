from django.shortcuts import render, redirect
from .models import User


def login_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_pw = request.POST.get('user_pw')

        try:
            user = User.objects.get(user_id=user_id, user_pw=user_pw)
            return redirect('/main/')
        except User.DoesNotExist:
            return render(request, 'login.html', {
                'error': '아이디 또는 비밀번호가 틀렸습니다.'
            })

    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_pw = request.POST.get('user_pw')

        if user_id == '' or user_pw == '':
            return render(request, 'register.html', {
                'error': '아이디와 비밀번호를 모두 입력해주세요.'
            })

        if User.objects.filter(user_id=user_id).exists():
            return render(request, 'register.html', {
                'error': '이미 존재하는 아이디입니다.'
            })

        User.objects.create(user_id=user_id, user_pw=user_pw)

        return render(request, 'register.html', {
            'success': '회원가입이 완료되었습니다. 로그인 화면으로 돌아가세요.'
        })

    return render(request, 'register.html')


def main_view(request):
    return render(request, 'main.html')