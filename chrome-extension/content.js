(() => {
  function getProblemTitle() {
    const titleElement = document.querySelector('meta[property="og:title"]') || document.querySelector('h1');
    if (titleElement) {
      return titleElement.content || titleElement.textContent?.trim() || '';
    }
    return '';
  }

  function getProblemUrl() {
    return window.location.href;
  }

  function sendProblemInfo() {
    const title = getProblemTitle();
    const url = getProblemUrl();
    chrome.runtime.sendMessage({ type: 'PROBLEM_INFO', title, url });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sendProblemInfo);
  } else {
    sendProblemInfo();
  }
})();
