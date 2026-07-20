(function attachHintCodeProviderAdapters(globalScope) {
  function cleanText(value) {
    return String(value || '').replace(/[\u0000-\u001f]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function compactStatus(value) {
    return cleanText(value).toLowerCase().replace(/[\s_:-]+/g, '');
  }

  function text(selector) {
    const element = document.querySelector(selector);
    return cleanText(element?.textContent || '');
  }

  function content(selector) {
    const element = document.querySelector(selector);
    return element?.content || '';
  }

  function editorText() {
    const textarea = document.querySelector('textarea');
    if (textarea?.value) {
      return textarea.value;
    }
    return cleanText(Array.from(document.querySelectorAll('.view-line, .cm-line')).map((line) => line.textContent || '').join('\n'));
  }

  function cleanTitle(value) {
    return cleanText(value).replace(/- LeetCode$/i, '').trim();
  }

  const adapters = {
    programmers: {
      hosts: ['school.programmers.co.kr', 'programmers.co.kr'],
      problemId(url) {
        const parts = url.pathname.split('/').filter(Boolean);
        const index = parts.indexOf('lessons');
        return index >= 0 && parts[index + 1] ? parts[index + 1] : '';
      },
      title() {
        return text('h1') || content('meta[property="og:title"]') || document.title || '';
      },
      language() {
        return text('.select-language, [data-testid="language-select"], button[aria-haspopup="listbox"]') || '';
      },
      sourceCode() {
        return editorText();
      },
      rawStatus() {
        return text('.modal-body, .submission-result, .result-message, [class*="result"], [class*="Result"]');
      },
      normalizeStatus(rawStatus) {
        const map = {
          '정답': 'accepted',
          '맞았습니다': 'accepted',
          accepted: 'accepted',
          '실행중': 'pending',
          '채점중': 'pending',
          pending: 'pending',
          '오답': 'wrong_answer',
          wronganswer: 'wrong_answer',
          '런타임에러': 'runtime_error',
          runtimeerror: 'runtime_error',
          '시간초과': 'time_limit_exceeded',
          timelimitexceeded: 'time_limit_exceeded',
          '메모리초과': 'memory_limit_exceeded',
          memorylimitexceeded: 'memory_limit_exceeded',
          '컴파일에러': 'compile_error',
          compileerror: 'compile_error',
          '취소': 'cancelled',
          cancelled: 'cancelled',
        };
        return map[compactStatus(rawStatus)] || 'unknown';
      },
    },
    leetcode: {
      hosts: ['leetcode.com'],
      problemId(url) {
        const parts = url.pathname.split('/').filter(Boolean);
        const index = parts.indexOf('problems');
        return index >= 0 && parts[index + 1] ? parts[index + 1] : '';
      },
      title() {
        return text('[data-cy="question-title"]') || content('meta[property="og:title"]') || document.title || '';
      },
      language() {
        return text('[data-cy="lang-select"], button[id*="headlessui-listbox-button"], button[aria-haspopup="listbox"]') || '';
      },
      sourceCode() {
        return editorText();
      },
      rawStatus() {
        return text('[data-e2e-locator="console-result"], [class*="result"], [class*="Result"], [data-cy="judgement-status"]');
      },
      normalizeStatus(rawStatus) {
        const map = {
          accepted: 'accepted',
          wronganswer: 'wrong_answer',
          runtimeerror: 'runtime_error',
          timelimitexceeded: 'time_limit_exceeded',
          memorylimitexceeded: 'memory_limit_exceeded',
          compileerror: 'compile_error',
          compilationerror: 'compile_error',
          pending: 'pending',
          running: 'pending',
          cancelled: 'cancelled',
          canceled: 'cancelled',
        };
        return map[compactStatus(rawStatus)] || 'unknown';
      },
    },
  };

  function detect(urlLike) {
    const url = typeof urlLike === 'string' ? new URL(urlLike) : urlLike;
    const host = url.hostname.toLowerCase();
    const match = Object.entries(adapters).find(([, adapter]) => adapter.hosts.some((supported) => host === supported || host.endsWith(`.${supported}`)));
    if (!match) {
      return null;
    }
    return { provider: match[0], adapter: match[1] };
  }

  globalScope.HintCodeProviderAdapters = {
    detect,
    cleanText,
    cleanTitle,
  };
})(globalThis);
