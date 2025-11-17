let tabId = null;

chrome.action.onClicked.addListener(async () => {
  const url = chrome.runtime.getURL('page.html');

  if (tabId) {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (tab) {
        await chrome.tabs.update(tabId, { active: true });
        return;
      }
    } catch (err) {
      tabId = null;
    }
  }

  const tab = await chrome.tabs.create({ url });
  tabId = tab.id;
});

chrome.tabs.onRemoved.addListener((closedId) => {
  if (closedId === tabId) {
    tabId = null;
  }
});
