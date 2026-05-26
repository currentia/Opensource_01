/* ── 비밀번호 토글 ── */
function togglePassword(targetId, eyeOnId, eyeOffId) {
  const input  = document.getElementById(targetId);
  const eyeOn  = document.getElementById(eyeOnId);
  const eyeOff = document.getElementById(eyeOffId);

  if (input.type === 'password') {
    input.type           = 'text';
    eyeOn.style.display  = 'none';
    eyeOff.style.display = 'inline';
  } else {
    input.type           = 'password';
    eyeOn.style.display  = 'inline';
    eyeOff.style.display = 'none';
  }
}

/* ── 유효성 검사 ── */
function validate() {
  let valid = true;

  const fields = ['username', 'password1', 'password2', 'name', 'birth', 'daily_budget'];

  // 에러 초기화
  fields.forEach(function (id) {
    const input = document.getElementById(id);
    const err   = document.getElementById(id + '-error');
    if (input) input.classList.remove('error');
    if (err)   err.classList.remove('visible');
  });

  // 아이디
  const username = document.getElementById('username');
  if (username.value.trim() === '') {
    setError('username', '아이디를 입력해 주세요.');
    valid = false;
  } else if (username.value.length < 4) {
    setError('username', '아이디는 4자 이상이어야 합니다.');
    valid = false;
  }

  // 비밀번호
  const pw1 = document.getElementById('password1');
  if (pw1.value.trim() === '') {
    setError('password1', '비밀번호를 입력해 주세요.');
    valid = false;
  } else if (pw1.value.length < 8) {
    setError('password1', '비밀번호는 8자 이상이어야 합니다.');
    valid = false;
  }

  // 비밀번호 확인
  const pw2 = document.getElementById('password2');
  if (pw2.value.trim() === '') {
    setError('password2', '비밀번호 확인을 입력해 주세요.');
    valid = false;
  } else if (pw1.value !== pw2.value) {
    setError('password2', '비밀번호가 일치하지 않습니다.');
    valid = false;
  }

  // 이름
  const name = document.getElementById('name');
  if (name.value.trim() === '') {
    setError('name', '이름을 입력해 주세요.');
    valid = false;
  }

  // 생년월일
  const birth = document.getElementById('birth');
  if (birth.value === '') {
    setError('birth', '생년월일을 입력해 주세요.');
    valid = false;
  }

  // 일 목표 금액
  const budget = document.getElementById('daily_budget');
  if (budget.value.trim() === '' || parseInt(budget.value) <= 0) {
    setError('daily_budget', '올바른 금액을 입력해 주세요.');
    valid = false;
  }

  return valid;
}

function setError(id, message) {
  const input = document.getElementById(id);
  const err   = document.getElementById(id + '-error');
  if (input) input.classList.add('error');
  if (err) {
    err.textContent = message;
    err.classList.add('visible');
  }
}

/* ── 이벤트 등록 ── */
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('signup-form');

  form.addEventListener('submit', function (e) {
    if (!validate()) e.preventDefault();
  });

  // 입력 시 에러 해제
  ['username', 'password1', 'password2', 'name', 'birth', 'daily_budget'].forEach(function (id) {
    const input = document.getElementById(id);
    const err   = document.getElementById(id + '-error');
    if (input) {
      input.addEventListener('input', function () {
        input.classList.remove('error');
        if (err) err.classList.remove('visible');
      });
    }
  });
});
