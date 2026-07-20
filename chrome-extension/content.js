(() => {
  const NORMALIZED_STATUSES = new Set([
    'pending',
    'accepted',
    'wrong_answer',
    'runtime_error',
    'time_limit_exceeded',
    'memory_limit_exceeded',
    'compile_error',
    'cancelled',
    'unknown',
  ]);

  let lastSentKey = '';

  function getProblemInfo() {
    const detected = globalThis.HintCodeProviderAdapters.detect(window.location.href);
    if (!detected) {
      return null;
    }
    const { provider, adapter } = detected;
    const url = new URL(window.location.href);
    return {
      provider,
      provider_problem_id: adapter.problemId(url),
      title: globalThis.HintCodeProviderAdapters.cleanTitle(adapter.title()),
      url: window.location.href,
      language: globalThis.HintCodeProviderAdapters.cleanText(adapter.language()),
    };
  }

  function sendProblemInfo() {
    const info = getProblemInfo();
    if (info) {
      chrome.runtime.sendMessage({ type: 'PROBLEM_INFO', ...info });
    }
  }

  async function detectAndSendSubmissionResult() {
    const detected = globalThis.HintCodeProviderAdapters.detect(window.location.href);
    const info = getProblemInfo();
    if (!detected || !info || !info.provider_problem_id) {
      return;
    }

    const rawStatus = globalThis.HintCodeProviderAdapters.cleanText(detected.adapter.rawStatus());
    const normalizedStatus = detected.adapter.normalizeStatus(rawStatus);
    if (!rawStatus || !NORMALIZED_STATUSES.has(normalizedStatus) || normalizedStatus === 'unknown') {
      return;
    }

    const payload = {
      provider: info.provider,
      provider_problem_id: info.provider_problem_id,
      problem_url: info.url,
      language: info.language,
      source_code_hash: await sha256(detected.adapter.sourceCode()),
      raw_status: rawStatus.slice(0, 255),
      normalized_status: normalizedStatus,
      submitted_at: new Date().toISOString(),
    };
    const dedupeKey = JSON.stringify(payload);
    if (dedupeKey === lastSentKey) {
      return;
    }
    lastSentKey = dedupeKey;

    chrome.runtime.sendMessage({ type: 'SUBMISSION_RESULT', payload });
  }

  function observeSubmissionResults() {
    const observer = new MutationObserver(() => {
      window.clearTimeout(observeSubmissionResults.timer);
      observeSubmissionResults.timer = window.setTimeout(detectAndSendSubmissionResult, 700);
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  async function sha256(value) {
    const bytes = new TextEncoder().encode(String(value || ''));
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      sendProblemInfo();
      observeSubmissionResults();
    });
  } else {
    sendProblemInfo();
    observeSubmissionResults();
  }
})();
