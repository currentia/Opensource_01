function goToLogin() {
    window.location.href = "login.html";
}

function handleLogin() {
    alert("로그인을 시도합니다.");
}

function goToSignup() {
    alert("회원가입 페이지로 이동합니다.");
}

function createCalendar() {
    const tbody = document.getElementById('calendarBody');
    if (!tbody) return;

    let date = 1;
    const startDay = 5; // 2026년 5월 1일은 금요일
    
    for (let i = 0; i < 6; i++) {
        let row = document.createElement('tr');
        for (let j = 0; j < 7; j++) {
            let cell = document.createElement('td');
            
            if (i === 0 && j < startDay) {
                cell.innerText = "";
            } else if (date > 31) {
                cell.innerText = "";
            } else {
                cell.innerText = date;

                
                if (j === 0) cell.classList.add('sun');
                else if (j === 6) cell.classList.add('sat');
                
                
                if (date === 5 || date === 25) cell.classList.add('holiday');

                date++;
            }
            row.appendChild(cell);
        }
        tbody.appendChild(row);
        if (date > 31) break;
    }
}

window.onload = createCalendar;


// 기존 코드들은 그대로 두시고, 맨 아래에 추가하세요!

function handleSignup() {
    const name = document.getElementById('newName').value;
    if(name === "") {
        alert("이름을 입력해주세요!");
    } else {
        alert(name + "님, 회원가입이 완료되었습니다!");
        window.location.href = "login.html"; // 가입 성공하면 로그인창으로 이동
    }
}

// 로그인창에서 '회원가입' 글자를 눌렀을 때 이동하는 기능 수정
function goToSignup() {
    window.location.href = "signup.html";
}// 기존 코드들은 그대로 두시고, 맨 아래에 추가하세요!

function handleSignup() {
    const name = document.getElementById('newName').value;
    if(name === "") {
        alert("이름을 입력해주세요!");
    } else {
        alert(name + "님, 회원가입이 완료되었습니다!");
        window.location.href = "login.html"; // 가입 성공하면 로그인창으로 이동
    }
}

// 로그인창에서 '회원가입' 글자를 눌렀을 때 이동하는 기능 수정
function goToSignup() {
    window.location.href = "signup.html";
}// 기존 코드들은 그대로 두시고, 맨 아래에 추가하세요!

function handleSignup() {
    const name = document.getElementById('newName').value;
    if(name === "") {
        alert("이름을 입력해주세요!");
    } else {
        alert(name + "님, 회원가입이 완료되었습니다!");
        window.location.href = "login.html"; // 가입 성공하면 로그인창으로 이동
    }
}

// 로그인창에서 '회원가입' 글자를 눌렀을 때 이동하는 기능 수정
function goToSignup() {
    window.location.href = "signup.html";
}