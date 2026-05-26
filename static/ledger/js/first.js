const today     = new Date();
let   viewYear  = today.getFullYear();
let   viewMonth = today.getMonth();

function renderCalendar() {
  document.getElementById('cal-title').textContent =
    viewYear + '년 ' + (viewMonth + 1) + '월';

  const grid     = document.getElementById('cal-grid');
  grid.innerHTML = '';

  const firstDay    = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const daysInPrev  = new Date(viewYear, viewMonth, 0).getDate();

  // 이전 달 잔여 날짜
  for (let i = 0; i < firstDay; i++) {
    grid.appendChild(createCell(
      daysInPrev - firstDay + 1 + i,
      i,
      true
    ));
  }

  // 이번 달 날짜
  for (let day = 1; day <= daysInMonth; day++) {
    const dow     = (firstDay + day - 1) % 7;
    const isToday =
      day === today.getDate() &&
      viewMonth === today.getMonth() &&
      viewYear  === today.getFullYear();

    grid.appendChild(createCell(day, dow, false, isToday));
  }

  // 다음 달 시작 날짜
  const total     = firstDay + daysInMonth;
  const remaining = total % 7 === 0 ? 0 : 7 - (total % 7);
  for (let i = 1; i <= remaining; i++) {
    grid.appendChild(createCell(i, (total + i - 1) % 7, true));
  }
}

/**
 * 날짜 셀 DOM 요소 생성
 * @param {number}  day        - 표시할 날짜 숫자
 * @param {number}  dow        - 요일 인덱스 (0=일 ~ 6=토)
 * @param {boolean} otherMonth - 이전/다음 달 여부
 * @param {boolean} isToday    - 오늘 여부
 * @returns {HTMLElement}
 */
function createCell(day, dow, otherMonth = false, isToday = false) {
  const d = document.createElement('div');

  let cls = 'cell';
  if (otherMonth) cls += ' other-month';
  if (dow === 0)  cls += ' sun-col';
  if (dow === 6)  cls += ' sat-col';
  if (isToday)    cls += ' today';

  d.className   = cls;
  d.textContent = day;
  return d;
}

function changeMonth(dir) {
  viewMonth += dir;
  if (viewMonth > 11) { viewMonth = 0; viewYear++; }
  if (viewMonth < 0)  { viewMonth = 11; viewYear--; }
  renderCalendar();
}

document.addEventListener('DOMContentLoaded', renderCalendar);
