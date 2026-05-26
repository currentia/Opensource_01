function togglePassword() {
  const input  = document.getElementById('password');
  const eyeOn  = document.getElementById('eye-on');
  const eyeOff = document.getElementById('eye-off');
  if (input.type === 'password') {
    input.type = 'text';
    eyeOn.style.display  = 'none';
    eyeOff.style.display = 'inline';
  } else {
    input.type = 'password';
    eyeOn.style.display  = 'inline';
    eyeOff.style.display = 'none';
  }
}

function validate() {
  let valid = true;
  const username    = document.getElementById('username');
  const password    = document.getElementById('password');
  const usernameErr = document.getElementById('username-error');
  const passwordErr = document.getElementById('password-error');

  username.classList.remove('error');
  password.classList.remove('error');
  usernameErr.classList.remove('visible');
  passwordErr.classList.remove('visible');

  if (username.value.trim() === '') {
    username.classList.add('error');
    usernameErr.textContent = '아이디를 입력해 주세요.';
    usernameErr.classList.add('visible');
    valid = false;
  }
  if (password.value.trim() === '') {
    password.classList.add('error');
    passwordErr.textContent = '비밀번호를 입력해 주세요.';
    passwordErr.classList.add('visible');
    valid = false;
  }
  return valid;
}

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('login-form');
  form.addEventListener('submit', function (e) {
    if (!validate()) e.preventDefault();
  });
  ['username', 'password'].forEach(function (id) {
    const input = document.getElementById(id);
    const err   = document.getElementById(id + '-error');
    input.addEventListener('input', function () {
      input.classList.remove('error');
      err.classList.remove('visible');
    });
  });
});
