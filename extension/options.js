const input = document.getElementById("url");
const status = document.getElementById("status");

browser.storage.local.get("serverUrl").then(({ serverUrl }) => {
  input.value = serverUrl || "http://10.10.10.10:8000/page";
});

document.getElementById("save").addEventListener("click", async () => {
  await browser.storage.local.set({ serverUrl: input.value.trim() });
  status.textContent = " Zapisano";
  setTimeout(() => (status.textContent = ""), 1500);
});
