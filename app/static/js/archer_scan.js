(function () {
  const recentBtn = document.getElementById("scan-recent-btn");
  const fullBtn = document.getElementById("scan-full-btn");
  const progressEl = document.getElementById("scan-progress");
  const progressFill = document.getElementById("scan-progress-fill");
  const statusText = document.getElementById("scan-status-text");
  let pollTimer = null;

  function setScanning(active) {
    if (recentBtn) recentBtn.disabled = active;
    if (fullBtn) fullBtn.disabled = active;
    if (progressEl) progressEl.classList.toggle("hidden", !active);
  }

  function updateProgress(data) {
    const total = data.progress_total || 0;
    const current = data.progress_current || 0;
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    if (progressFill) progressFill.style.width = pct + "%";
    if (statusText) {
      statusText.textContent =
        data.status === "running"
          ? `Scanning ${current} of ${total}… Added ${data.tournaments_added}, skipped ${data.tournaments_skipped}`
          : data.status === "completed"
            ? `Done. Added ${data.tournaments_added} tournament(s).`
            : data.status === "failed"
              ? `Failed: ${data.error_message || "Unknown error"}`
              : "Starting scan…";
    }
  }

  function pollJob(jobId) {
    fetch(`/my-results/scan/${jobId}`, { headers: { Accept: "application/json" } })
      .then((r) => r.json())
      .then((data) => {
        updateProgress(data);
        if (data.status === "running" || data.status === "pending") {
          pollTimer = setTimeout(() => pollJob(jobId), 2000);
        } else {
          setScanning(false);
          if (data.status === "completed") {
            window.location.reload();
          }
        }
      })
      .catch(() => {
        setScanning(false);
        if (statusText) statusText.textContent = "Could not check scan status.";
      });
  }

  function startScan(scope) {
    setScanning(true);
    if (statusText) statusText.textContent = "Starting scan…";
    fetch("/my-results/scan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ scope }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setScanning(false);
          if (statusText) statusText.textContent = data.error;
          return;
        }
        pollJob(data.job_id);
      })
      .catch(() => {
        setScanning(false);
        if (statusText) statusText.textContent = "Could not start scan.";
      });
  }

  if (recentBtn) {
    recentBtn.addEventListener("click", () => startScan("recent"));
  }
  if (fullBtn) {
    fullBtn.addEventListener("click", () => {
      if (confirm("Scan all tournament history? This may take a long time.")) {
        startScan("full_history");
      }
    });
  }
  if (window.__archerScanJobId) {
    setScanning(true);
    pollJob(window.__archerScanJobId);
  }
})();
