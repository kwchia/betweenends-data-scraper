(function () {
  const searchInput = document.getElementById("tournament-search");
  const resultsList = document.getElementById("search-results");
  const tournamentIdInput = document.getElementById("tournament-id");
  const selectedDiv = document.getElementById("selected-tournament");
  const viewBtn = document.getElementById("view-results");
  const clubSelect = document.getElementById("club-select");
  const form = document.getElementById("search-form");

  if (!searchInput) return;

  const resultsUrlTemplate = window.TOURNAMENT_RESULTS_URL || "/tournaments/0/results";
  const searchUrl = window.TOURNAMENT_SEARCH_URL || "/tournaments/search";

  let debounceTimer;

  function showLoading() {
    var existing = document.getElementById("results-loading");
    if (existing) {
      existing.hidden = false;
      return;
    }
    var overlay = document.createElement("div");
    overlay.id = "results-loading";
    overlay.className = "results-loading";
    overlay.setAttribute("role", "status");
    overlay.innerHTML = "<p>Compiling results… this may take a minute.</p>";
    document.body.appendChild(overlay);
  }

  searchInput.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    const q = searchInput.value.trim();
    if (q.length < 2) {
      resultsList.style.display = "none";
      return;
    }
    debounceTimer = setTimeout(function () {
      fetch(searchUrl + "?q=" + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          resultsList.innerHTML = "";
          if (data.error) return;
          data.forEach(function (t) {
            const li = document.createElement("li");
            li.textContent = t.name + (t.location ? " — " + t.location : "");
            li.dataset.id = t.id;
            li.addEventListener("click", function () {
              tournamentIdInput.value = t.id;
              searchInput.value = t.name;
              selectedDiv.textContent = t.name;
              resultsList.style.display = "none";
              viewBtn.disabled = false;
            });
            resultsList.appendChild(li);
          });
          resultsList.style.display = data.length ? "block" : "none";
        });
    }, 300);
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const tid = tournamentIdInput.value;
    const clubId = clubSelect.value;
    if (!tid) return;
    viewBtn.disabled = true;
    viewBtn.textContent = "Loading…";
    showLoading();
    const path = resultsUrlTemplate.replace("/0/", "/" + tid + "/");
    window.location.href = path + "?club_id=" + encodeURIComponent(clubId);
  });
})();
