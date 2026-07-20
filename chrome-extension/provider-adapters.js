function normalizeLanguage(rawLanguage) {
  const value = (rawLanguage || '').trim().toLowerCase();
  const languageMap = {
    python: 'Python',
    python3: 'Python',
    py: 'Python',
    java: 'Java',
    cpp: 'C++',
    'c++': 'C++',
    c: 'C',
    javascript: 'JavaScript',
    js: 'JavaScript',
  };
  return languageMap[value] || rawLanguage || '';
}

function getMetaTitle() {
  const ogTitle = document.querySelector('meta[property="og:title"]');
  const heading = document.querySelector('h1');
  return (ogTitle?.content || heading?.textContent || document.title || '').trim();
}

function getSelectedLanguage() {
  const selectors = [
    '[data-cy="lang-select"]',
    '.ant-select-selection-item',
    'select',
    '[aria-label*="language" i]',
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    const text = element?.value || element?.textContent;
    if (text && text.trim()) {
      return normalizeLanguage(text);
    }
  }

  return '';
}

function getStarterCode() {
  const selectors = [
    'textarea',
    '.view-lines',
    '.monaco-editor',
    'pre code',
    'code',
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    const text = element?.value || element?.innerText || element?.textContent;
    if (text && text.trim()) {
      return text.trim();
    }
  }

  return '';
}

function extractLeetCodeProblemId(url) {
  const match = url.pathname.match(/\/problems\/([^/]+)/);
  return match ? match[1] : '';
}

function extractProgrammersProblemId(url) {
  const match = url.pathname.match(/\/lessons\/(\d+)/);
  return match ? match[1] : '';
}

class LeetCodeProvider {
  static provider = 'leetcode';

  static importProblem(url) {
    return {
      provider: this.provider,
      problem_id: extractLeetCodeProblemId(url),
      title: getMetaTitle(),
      url: url.href,
      language: getSelectedLanguage(),
      starter_code: getStarterCode(),
      metadata: {
        hostname: url.hostname,
        pathname: url.pathname,
      },
    };
  }
}

class ProgrammersProvider {
  static provider = 'programmers';

  static importProblem(url) {
    return {
      provider: this.provider,
      problem_id: extractProgrammersProblemId(url),
      title: getMetaTitle(),
      url: url.href,
      language: getSelectedLanguage(),
      starter_code: getStarterCode(),
      metadata: {
        hostname: url.hostname,
        pathname: url.pathname,
      },
    };
  }
}

function importProviderProblem(provider, href) {
  const url = new URL(href);
  if (provider === 'leetcode') {
    return LeetCodeProvider.importProblem(url);
  }
  if (provider === 'programmers') {
    return ProgrammersProvider.importProblem(url);
  }
  return {
    provider,
    problem_id: '',
    title: getMetaTitle(),
    url: url.href,
    language: getSelectedLanguage(),
    starter_code: getStarterCode(),
    metadata: {
      hostname: url.hostname,
      pathname: url.pathname,
    },
  };
}

if (typeof module !== 'undefined') {
  module.exports = {
    detectProvider: typeof detectProvider === 'function' ? detectProvider : undefined,
    importProviderProblem,
    LeetCodeProvider,
    ProgrammersProvider,
  };
}
