// Minimal MV3 service worker — keeps the extension alive when needed.
chrome.runtime.onInstalled.addListener(() => {
  console.log("Briefly AI extension installed.");
});
