// ── Elements ───────────────────────────────────────────────────────────────
function els() {
    return {
        wrap:    document.getElementById("progress-wrap"),
        bar:     document.getElementById("progress-bar"),
        label:   document.getElementById("progress-label"),
        counter: document.getElementById("progress-counter")
    };
}

// ── Show determinate progress ──────────────────────────────────────────────
function showProgress(label, counter, pct) {
    const e = els();
    if (!e.wrap) return;

    e.wrap.style.display = "block";
    e.bar.classList.remove("progress-bar--indeterminate");

    if (label  !== undefined && e.label)   e.label.textContent = label;
    if (counter !== undefined && e.counter) {
        e.counter.textContent = counter || "";
        e.counter.style.display = counter ? "block" : "none";
    }
    if (pct !== undefined) {
        const p = Math.min(pct, 100);
        e.bar.style.width = p + "%";
        e.bar.setAttribute("aria-valuenow", p);
    }
}

// ── Show indeterminate (pulsing) progress ──────────────────────────────────
function showProgressIndeterminate(label) {
    const e = els();
    if (!e.wrap) return;

    e.wrap.style.display = "block";
    if (e.label) e.label.textContent = label || "";
    if (e.counter) { e.counter.textContent = ""; e.counter.style.display = "none"; }
    e.bar.classList.add("progress-bar--indeterminate");
}

// ── Hide progress bar ──────────────────────────────────────────────────────
function hideProgress() {
    const e = els();
    if (!e.wrap) return;
    setTimeout(() => {
        e.wrap.style.display = "none";
        e.bar.classList.remove("progress-bar--indeterminate");
        e.bar.style.width = "0%";
        if (e.label)   e.label.textContent = "";
        if (e.counter) { e.counter.textContent = ""; e.counter.style.display = "none"; }
    }, 700);
}

// ── Download progress via SSE ──────────────────────────────────────────────
function startDownloadProgressBar(jobId, onComplete) {
    showProgressIndeterminate("Preparing download...");

    const interval = setInterval(async () => {
        try {
            const res  = await fetch("/download_progress/" + jobId);
            const data = await res.json();

            for (const event of data.events) {
                if (event.status === "progress") {
                    const pct     = Math.min(event.percent || 0, 100);
                    const counter = (event.total && event.total > 1)
                        ? `${event.current} / ${event.total} videos`
                        : null;
                    const label   = event.filename
                        ? `Downloading: ${event.filename}`
                        : "Downloading...";
                    showProgress(label, counter, pct);
                }
            }

            if (data.error) {
                clearInterval(interval);
                hideProgress();
                toast("Download failed: " + data.error, "error");
                return;
            }

            if (data.done) {
                clearInterval(interval);
                showProgress("Complete!", null, 100);
                setTimeout(() => hideProgress(), 700);
                if (onComplete) onComplete();
            }

        } catch (err) {
            clearInterval(interval);
            hideProgress();
            toast("Connection lost during download.", "error");
        }
    }, 400);
}