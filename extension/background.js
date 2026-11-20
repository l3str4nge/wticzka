const DEFAULT_URL = "http://10.10.10.10:8000/page";

async function getServerUrl() {
  const { serverUrl } = await browser.storage.local.get("serverUrl");
  return serverUrl || DEFAULT_URL;
}

function setBadge(tabId, text, color, title = "Wyślij stronę na serwer") {
  browser.browserAction.setBadgeText({ text, tabId });
  browser.browserAction.setTitle({ title, tabId });
  browser.browserAction.setBadgeBackgroundColor({ color, tabId });
  setTimeout(() => browser.browserAction.setBadgeText({ text: "", tabId }), 3000);
}

browser.browserAction.onClicked.addListener(async (tab) => {
  let serverUrl = "";
  try {
    serverUrl = await getServerUrl();
    const [page] = await browser.tabs.executeScript(tab.id, {
      code: `({
        url: location.href,
        title: document.title,
        html: document.documentElement.outerHTML,
        text: document.body ? document.body.innerText : ""
      })`
    });

    const res = await fetch(serverUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...page, sentAt: new Date().toISOString() })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    setBadge(tab.id, "OK", "#2e7d32");
  } catch (err) {
    console.error("Wysyłanie nie powiodło się:", err);
    setBadge(tab.id, "ERR", "#c62828", `Błąd (${serverUrl}): ${err.message}`);
  }
});
