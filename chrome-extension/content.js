(() => {
  function sendProblemInfo() {
    const provider = detectProvider(window.location.href);
    if (!provider) {
      chrome.runtime.sendMessage({ type: 'PROBLEM_INFO_UNSUPPORTED', url: window.location.href });
      return;
    }

    const problem = importProviderProblem(provider, window.location.href);
    chrome.runtime.sendMessage({ type: 'PROBLEM_INFO', problem });
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type !== 'GET_PROBLEM_INFO') {
      return false;
    }

    const provider = detectProvider(window.location.href);
    if (!provider) {
      sendResponse({ problem: null });
      return false;
    }

    sendResponse({ problem: importProviderProblem(provider, window.location.href) });
    return false;
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sendProblemInfo);
  } else {
    sendProblemInfo();
  }
})();
