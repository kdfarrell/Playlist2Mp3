(function () {

    const DURATION = 3500;


    // ----- CONTAINER -----

    function createContainer() {
        // Create the toast container once and reuse it for all toasts
        let c = document.getElementById("toast-container");
        if (!c) {
            c = document.createElement("div");
            c.id = "toast-container";
            document.body.appendChild(c);
        }
        return c;
    }


    // ----- TOAST -----

    // type: "info" | "success" | "error" | "warning"
    window.toast = function (message, type = "info") {
        const container = createContainer();

        const el = document.createElement("div");
        el.className   = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);

        // Double rAF ensures the element is painted before the transition starts
        requestAnimationFrame(() => {
            requestAnimationFrame(() => el.classList.add("toast-show"));
        });

        // Warning toasts stay longer since they carry more information
        const duration = type === "warning" ? 5000 : DURATION;

        setTimeout(() => {
            el.classList.remove("toast-show");
            el.addEventListener("transitionend", () => el.remove(), { once: true });
        }, duration);
    };

})();