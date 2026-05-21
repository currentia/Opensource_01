from django.shortcuts import render, redirect
from .models import User


def login_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_pw = request.POST.get('user_pw')

        if User.objects.filter(user_id=user_id, user_pw=user_pw).exists():
           request.session['user_id'] = user_id
           return redirect('/main/')
        else:
            return render(request, 'login.html', {
                'error': '아이디 또는 비밀번호가 틀렸습니다.'
            })

    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_pw = request.POST.get('user_pw')

        if not user_id or not user_pw:
            return render(request, 'register.html', {
                'error': '아이디와 비밀번호를 모두 입력해주세요.'
            })

        if User.objects.filter(user_id=user_id).exists():
            return render(request, 'register.html', {
                'error': '이미 존재하는 아이디입니다.'
            })

        User.objects.create(user_id=user_id, user_pw=user_pw)

        return render(request, 'register.html', {
            'success': '회원가입 완료!'
        })

    return render(request, 'register.html')


def main_view(request):
    return render(request, 'main.html')


def logout_view(request):
    return redirect('/')
from .models import Friend


def friend_view(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('/')

    user = User.objects.get(user_id=user_id)
    message = None

    if request.method == "POST":
        friend_id = request.POST.get("friend_id")

        if friend_id == user.user_id:
            message = "자기 자신은 친구로 추가할 수 없습니다."

        elif not User.objects.filter(user_id=friend_id).exists():
            message = "존재하지 않는 아이디입니다."

        else:
            friend_user = User.objects.get(user_id=friend_id)

            if Friend.objects.filter(user=user, friend=friend_user).exists():
                message = "이미 추가된 친구입니다."
            else:
                Friend.objects.create(user=user, friend=friend_user)
                message = "친구가 추가되었습니다."

    friends = Friend.objects.filter(user=user).distinct()

    return render(request, "friend.html", {
        "friends": friends,
        "message": message
    })