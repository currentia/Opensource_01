const rangeInput   = document.getElementById('ratio_limit');
  const ratioDisplay = document.getElementById('ratio-display');
  const ratioDesc    = document.getElementById('ratio-desc');

  function updateRatio(val) {
    const pct = Math.round(val * 100);
    ratioDisplay.textContent = pct + '%';
    ratioDesc.textContent    = '하루 지출의 ' + pct + '% 이하면 달성';
  }

  rangeInput.addEventListener('input', (e) => updateRatio(e.target.value));
  updateRatio(rangeInput.value);