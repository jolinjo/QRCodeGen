chrome.action.onClicked.addListener(async () => {
  const pageUrl = chrome.runtime.getURL('page.html');

  try {
    const tabs = await chrome.tabs.query({ url: pageUrl });
    if (tabs && tabs.length > 0) {
      const tab = tabs[0];
      chrome.tabs.update(tab.id, { active: true });
      return;
    }
  } catch (error) {
    console.error('查詢頁籤失敗:', error);
  }

  chrome.tabs.create({ url: pageUrl });
});
