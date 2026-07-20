(() => {
  const provider = 'LeetCode';
  const problemId = () => location.pathname.split('/').filter(Boolean)[1] || '';
  const normalize = (text) => {
    const value = (text || '').toLowerCase();
    if (value.includes('accepted')) return 'Accepted';
    if (value.includes('wrong answer')) return 'Wrong Answer';
    if (value.includes('runtime error')) return 'Runtime Error';
    if (value.includes('time limit exceeded')) return 'Time Limit Exceeded';
    if (value.includes('compile error')) return 'Compile Error';
    return 'Unknown';
  };
  const editor = () => document.querySelector('.monaco-editor textarea, textarea');
  const report = () => {
    const result = document.querySelector('[data-e2e-locator="submission-result"], [class*="result"]')?.innerText;
    if (result) chrome.runtime.sendMessage({type: 'HINTCODE_PROVIDER_RESULT', payload: {provider, providerProblemId: problemId(), status: normalize(result)}});
  };
  new MutationObserver(report).observe(document.documentElement, {childList: true, subtree: true});
  chrome.runtime.onMessage.addListener((message, _sender, respond) => {
    if (message.type !== 'HINTCODE_TRANSFER' || message.provider !== provider || message.providerProblemId !== problemId()) return;
    const target = editor();
    if (!target) return respond({ok: false, status: 'Transfer unsupported'});
    target.focus(); target.value = message.code; target.dispatchEvent(new Event('input', {bubbles: true}));
    respond({ok: true, status: 'Code transferred'});
  });
})();
