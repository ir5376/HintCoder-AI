const statusEl = document.getElementById('status');
const openButton = document.getElementById('openHintCode');

function showMessage(message) {
  statusEl.textContent = message;
}

async function getCurrentTabInfo() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function sendMessageToTab(tabId, message) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        resolve(null);
        return;
      }
      resolve(response);
    });
  });
}

async function loadInfo() {
  try {
    const tab = await getCurrentTabInfo();
    if (!tab || !tab.url) {
      showMessage('Open a supported coding problem page to continue.');
      return;
    }

    const provider = detectProvider(tab.url);

    if (!provider) {
      showMessage('This page is not a supported coding problem page.');
      return;
    }

    const response = await sendMessageToTab(tab.id, { type: 'GET_PROBLEM_INFO' });
    const problem = response?.problem || {
      provider,
      problem_id: '',
      title: tab.title || 'Unknown problem',
      url: tab.url,
      language: '',
      starter_code: '',
      metadata: {},
    };

    showMessage(`Provider: ${problem.provider}\nProblem: ${problem.title}\nURL: ${problem.url}`);
    openButton.disabled = false;
    openButton.dataset.problem = JSON.stringify(problem);
  } catch (error) {
    console.error(error);
    showMessage('Unable to read the current page.');
  }
}

function openHintCode() {
  const problem = JSON.parse(openButton.dataset.problem || '{}');

  if (!problem.title && !problem.url) {
    showMessage('No problem information available.');
    return;
  }

  const hintCodeUrl = new URL('http://localhost:8501');
  hintCodeUrl.searchParams.set('provider', problem.provider || '');
  hintCodeUrl.searchParams.set('problem_id', problem.problem_id || '');
  hintCodeUrl.searchParams.set('problem_title', problem.title || '');
  hintCodeUrl.searchParams.set('problem_url', problem.url || '');
  hintCodeUrl.searchParams.set('language', problem.language || '');

  window.open(hintCodeUrl.toString(), '_blank', 'noopener,noreferrer');
}

openButton.addEventListener('click', openHintCode);
openButton.disabled = true;
loadInfo();
