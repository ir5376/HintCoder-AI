(() => {
  const provider = 'Programmers';
  const problemId = () => location.pathname.match(/lessons\/(\d+)/)?.[1] || '';
  const normalize = (text) => {
    const value = (text || '').toLowerCase();
    if (value.includes('정답') || value.includes('accepted')) return 'Accepted';
    if (value.includes('오답') || value.includes('wrong answer')) return 'Wrong Answer';
    if (value.includes('runtime error')) return 'Runtime Error';
    if (value.includes('time limit')) return 'Time Limit Exceeded';
    if (value.includes('compile error')) return 'Compile Error';
    return 'Unknown';
  };
  const editor = () => document.querySelector('.monaco-editor textarea, textarea.CodeMirror-input, textarea');
  const report = () => {
    const result = document.querySelector('.result, .challenge-result, [class*="result"]')?.innerText;
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
