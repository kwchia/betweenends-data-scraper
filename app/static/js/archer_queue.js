(function () {
  const searchInput = document.getElementById("archer-tournament-search");
  const resultsList = document.getElementById("archer-search-results");
  const tournamentIdInput = document.getElementById("archer-tournament-id");
  const selectedDiv = document.getElementById("archer-selected-tournament");
  const queueBtn = document.getElementById("archer-queue-btn");
  const queueList = document.getElementById("archer-queue-list");
  const queueEmpty = document.getElementById("archer-queue-empty");

  if (!searchInput) return;

  const searchUrl = window.ARCHER_SEARCH_URL;
  const queueUrl = window.ARCHER_QUEUE_URL;
  const queueListUrl = window.ARCHER_QUEUE_LIST_URL;
  const TERMINAL_STATUSES = ["completed", "failed", "not_found"];
  let debounceTimer;
  let pollTimer;
  let selectedName = "";
  let wasPollingActive = false;

  function isActive(item) {
    return item.status === "pending" || item.status === "processing";
  }

  function isTerminal(item) {
    return TERMINAL_STATUSES.indexOf(item.status) >= 0;
  }

  function clearPollTimer() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function schedulePoll(delay) {
    clearPollTimer();
    pollTimer = setTimeout(pollQueue, delay);
  }

  function reloadForQueueUpdate() {
    clearPollTimer();
    wasPollingActive = false;
    window.location.reload();
  }

  function renderQueue(activeItems) {
    if (!queueList) return;
    queueList.innerHTML = "";
    activeItems.forEach(function (item) {
      const li = document.createElement("li");
      const badge = document.createElement("span");
      li.className = "queue-item queue-" + item.status;
      li.dataset.id = item.id;
      li.appendChild(document.createTextNode(item.tournament_name));

      li.appendChild(document.createTextNode(" "));
      badge.className = "badge";
      badge.textContent = item.status;
      li.appendChild(badge);

      if (item.error_message) {
        const muted = document.createElement("span");
        li.appendChild(document.createTextNode(" "));
        muted.className = "muted";
        muted.textContent = item.error_message;
        li.appendChild(muted);
      }

      queueList.appendChild(li);
    });
    if (queueEmpty) {
      queueEmpty.classList.toggle("hidden", activeItems.length > 0);
    }
  }

  function pollQueue() {
    fetch(queueListUrl, { headers: { Accept: "application/json" } })
      .then(function (r) {
        return r.json();
      })
      .then(function (items) {
        const active = items.filter(isActive);
        renderQueue(active);
        if (wasPollingActive && active.length === 0) {
          reloadForQueueUpdate();
          return;
        }
        wasPollingActive = active.length > 0;
        if (active.length > 0) {
          schedulePoll(2000);
        } else {
          clearPollTimer();
        }
      })
      .catch(function () {
        schedulePoll(4000);
      });
  }

  function afterQueueChange(item) {
    if (isTerminal(item)) {
      reloadForQueueUpdate();
      return;
    }
    if (isActive(item)) {
      wasPollingActive = true;
      renderQueue([item]);
      pollQueue();
    }
  }

  searchInput.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    var q = searchInput.value.trim();
    if (q.length < 2) {
      resultsList.style.display = "none";
      return;
    }
    debounceTimer = setTimeout(function () {
      fetch(searchUrl + "?q=" + encodeURIComponent(q))
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          resultsList.innerHTML = "";
          if (data.error) return;
          data.forEach(function (t) {
            var li = document.createElement("li");
            li.textContent = t.name + (t.location ? " — " + t.location : "");
            li.dataset.id = t.id;
            li.dataset.name = t.name;
            li.addEventListener("click", function () {
              tournamentIdInput.value = t.id;
              selectedName = t.name;
              searchInput.value = t.name;
              selectedDiv.textContent = t.name;
              resultsList.style.display = "none";
              queueBtn.disabled = false;
            });
            resultsList.appendChild(li);
          });
          resultsList.style.display = data.length ? "block" : "none";
        });
    }, 300);
  });

  queueBtn.addEventListener("click", function () {
    var tid = tournamentIdInput.value;
    if (!tid) return;
    queueBtn.disabled = true;
    fetch(queueUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        tournament_id: parseInt(tid, 10),
        tournament_name: selectedName || searchInput.value,
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        queueBtn.disabled = false;
        if (data.error) {
          alert(data.error);
          return;
        }
        tournamentIdInput.value = "";
        searchInput.value = "";
        selectedDiv.textContent = "";
        selectedName = "";
        queueBtn.disabled = true;
        afterQueueChange(data);
      })
      .catch(function () {
        queueBtn.disabled = false;
        alert("Could not add to queue.");
      });
  });

  if (queueList && queueList.children.length) {
    wasPollingActive = true;
    pollQueue();
  }
})();
