const statusEl = document.getElementById('status');
const openButton = document.getElementById('openHintCode');

function showMessage(message) {
  statusEl.textContent = message;
}

async function getCurrentTabInfo() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function loadInfo() {
  try {
    const tab = await getCurrentTabInfo();
    if (!tab || !tab.url) {
      showMessage('Open a Programmers problem page to continue.');
      return;
    }

    const url = new URL(tab.url);
    const detected = globalThis.HintCodeProviderAdapters.detect(url);

    if (!detected) {
      showMessage('Open a LeetCode or Programmers problem page to continue.');
      return;
    }

    const provider = detected.provider;
    const providerProblemId = detected.adapter.problemId(url);
    const title = tab.title || 'Unknown problem';
    showMessage(`Problem: ${title}\nURL: ${tab.url}`);
    openButton.disabled = false;
    openButton.dataset.provider = provider;
    openButton.dataset.providerProblemId = providerProblemId;
    openButton.dataset.problemTitle = title;
    openButton.dataset.problemUrl = tab.url;
  } catch (error) {
    console.error(error);
    showMessage('Unable to read the current page.');
  }
}

function openHintCode() {
  const provider = openButton.dataset.provider || '';
  const providerProblemId = openButton.dataset.providerProblemId || '';
  const title = openButton.dataset.problemTitle || '';
  const problemUrl = openButton.dataset.problemUrl || '';

  if (!title && !problemUrl) {
    showMessage('No problem information available.');
    return;
  }

  const hintCodeUrl = new URL('http://localhost:8501');
  if (provider) {
    hintCodeUrl.searchParams.set('provider', provider);
  }
  if (providerProblemId) {
    hintCodeUrl.searchParams.set('problem_id', providerProblemId);
    hintCodeUrl.searchParams.set('provider_problem_id', providerProblemId);
  }
  hintCodeUrl.searchParams.set('problem_title', title);
  hintCodeUrl.searchParams.set('problem_url', problemUrl);

  window.open(hintCodeUrl.toString(), '_blank', 'noopener,noreferrer');
}

openButton.addEventListener('click', openHintCode);
openButton.disabled = true;
loadInfo();
