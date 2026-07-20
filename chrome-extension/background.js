const resultByProblem = new Map();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'HINTCODE_PROVIDER_RESULT') {
    const payload = {...message.payload, receivedAt: Date.now()};
    resultByProblem.set(`${payload.provider}:${payload.providerProblemId}`, payload);
    chrome.runtime.sendMessage({type: 'HINTCODE_RESULT_UPDATED', payload}).catch(() => {});
    sendResponse({ok: true});
    return;
  }
  if (message.type === 'HINTCODE_TRANSFER') {
    chrome.tabs.query({url: message.originalUrl}).then((tabs) => {
      const tab = tabs[0];
      if (!tab) return sendResponse({ok: false, status: 'Transfer unsupported'});
      chrome.tabs.update(tab.id, {active: true});
      chrome.tabs.sendMessage(tab.id, message, (response) => sendResponse(response || {ok: false, status: 'Transfer unsupported'}));
    });
    return true;
  }
  if (message.type === 'HINTCODE_GET_RESULT') {
    sendResponse(resultByProblem.get(`${message.provider}:${message.providerProblemId}`) || null);
  }
});
