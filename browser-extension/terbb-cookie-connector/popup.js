const APP_URL = "https://postx.179-197-73-32.sslip.io/app/contas/cookie";

chrome.storage.session.get("terbb_cookie_queue_v1").then((stored) => {
  const queue = stored.terbb_cookie_queue_v1;
  const count = Array.isArray(queue?.items) ? queue.items.length : 0;
  document.querySelector("#status").textContent = count
    ? `${count} conta${count === 1 ? "" : "s"} na fila temporária.`
    : "Nenhuma conta na fila temporária.";
});

document.querySelector("#open").addEventListener("click", () => {
  chrome.tabs.create({ url: APP_URL });
});
