(function () {
  const DURATION = 3500;

  function createContainer() {
    let c = document.getElementById("toast-container");
    if (!c) {
      c = document.createElement("div");
      c.id = "toast-container";
      document.body.appendChild(c);
    }
    return c;
  }

  // type: "info" | "success" | "error" | "warning"
  window.toast = function (message, type = "info") {
    const container = createContainer();
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.textContent = message;
    container.appendChild(el);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => el.classList.add("toast-show"));
    });

    // Warning toasts stay a bit longer since they have more info
    const duration = type === "warning" ? 5000 : DURATION;

    setTimeout(() => {
      el.classList.remove("toast-show");
      el.addEventListener("transitionend", () => el.remove(), { once: true });
    }, duration);
  };
})();