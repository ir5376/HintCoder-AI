const API_BASE_URL = 'http://localhost:8000';

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== 'SUBMISSION_RESULT' || !message.payload) {
    return false;
  }

  fetch(`${API_BASE_URL}/provider-submissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message.payload),
  })
    .then((response) => sendResponse({ ok: response.ok }))
    .catch((error) => sendResponse({ ok: false, error: String(error && error.message ? error.message : error) }));

  return true;
});
