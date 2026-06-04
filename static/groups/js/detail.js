 function goToMemberLedger() {
    const userId = document.getElementById('feedback-target').value;
    const date   = document.getElementById('feedback-date').value;

    if (!userId) { alert('대상 멤버를 선택해 주세요.'); return; }
    if (!date)   { alert('날짜를 선택해 주세요.'); return; }

    window.location.href = `/groups/{{ group.pk }}/ledger/${userId}/${date}/`;
  }