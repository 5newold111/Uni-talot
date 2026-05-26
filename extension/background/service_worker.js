chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "LOG") {
    console.log("[EC3D-Bridge]", message.text);
  }
  return true;
});
