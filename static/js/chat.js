// Auto-scroll to latest message
document.addEventListener("DOMContentLoaded", () => {
  const messages = document.getElementById("messages");
  messages.scrollTop = messages.scrollHeight;
});