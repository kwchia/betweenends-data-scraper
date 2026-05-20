(function () {
  const ARROW_VALUES = {
    M: 0, 0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9,
    T: 10, X: 10, W: 5, Y: 11, Z: 6, a: 11, b: 12, d: 14, E: 0, "!": 0,
  };

  const roundsContainer = document.getElementById("practice-rounds");
  const addBtn = document.getElementById("practice-add-round");
  const form = document.getElementById("practice-form");
  const summaryEl = document.getElementById("practice-score-summary");
  if (!roundsContainer || !addBtn) return;

  function arrowValue(ch) {
    if (!ch) return 0;
    return ARROW_VALUES[ch.toUpperCase()] ?? 0;
  }

  function getRoundIndex(fieldset) {
    return fieldset.dataset.roundIndex;
  }

  function getEntryMode(fieldset) {
    const idx = getRoundIndex(fieldset);
    return (
      fieldset.querySelector('input[name="entry_mode_' + idx + '"]:checked')?.value ||
      "total"
    );
  }

  function serializeArrowString(fieldset) {
    const idx = getRoundIndex(fieldset);
    const ape = parseInt(
      fieldset.querySelector(".arrows-per-end-input")?.value || "3",
      10
    );
    const numEnds = parseInt(
      fieldset.querySelector(".num-ends-input")?.value || "1",
      10
    );
    let s = "";
    for (let e = 0; e < numEnds; e++) {
      for (let a = 0; a < ape; a++) {
        const inp = fieldset.querySelector(
          'input[name="arrow_' + idx + "_" + e + "_" + a + '"]'
        );
        const v = (inp?.value || "").trim().toUpperCase();
        if (v) s += v[0];
      }
    }
    const hidden = fieldset.querySelector(".arrow-string-hidden");
    if (hidden) hidden.value = s;
    return s;
  }

  function scoreArrowString(str) {
    let total = 0;
    for (const ch of str) total += arrowValue(ch);
    return total;
  }

  function updateArrowGridTotals(fieldset) {
    const tbody = fieldset.querySelector(".practice-arrow-grid-body");
    if (!tbody) return;
    let running = 0;
    tbody.querySelectorAll("tr").forEach((row) => {
      let endTotal = 0;
      row.querySelectorAll(".arrow-cell-input").forEach((inp) => {
        endTotal += arrowValue((inp.value || "").trim());
      });
      running += endTotal;
      const endCell = row.querySelector(".end-total-cell");
      const runCell = row.querySelector(".running-total-cell");
      if (endCell) endCell.textContent = String(endTotal);
      if (runCell) runCell.textContent = String(running);
    });
    const roundTotal = fieldset.querySelector(".round-grid-total");
    if (roundTotal) roundTotal.textContent = String(running);
    serializeArrowString(fieldset);
    updatePracticeSummary();
  }

  function getRoundScore(fieldset) {
    if (getEntryMode(fieldset) === "total") {
      const v = parseInt(
        fieldset.querySelector(".round-total-input")?.value || "",
        10
      );
      return Number.isNaN(v) ? null : v;
    }
    const str = serializeArrowString(fieldset);
    return str ? scoreArrowString(str) : null;
  }

  function updatePracticeSummary() {
    if (!summaryEl) return;
    const rounds = roundsContainer.querySelectorAll(".practice-round");
    const parts = [];
    let combined = 0;
    let any = false;
    rounds.forEach((fs, i) => {
      const score = getRoundScore(fs);
      if (score !== null) {
        any = true;
        combined += score;
        parts.push("Round " + (i + 1) + ": " + score);
      }
    });
    if (!any) {
      summaryEl.textContent = "Enter scores below to see round totals.";
      return;
    }
    summaryEl.textContent =
      parts.join(" · ") + " · Combined total: " + combined;
  }

  function buildArrowGrid(fieldset, preserveValues) {
    const idx = getRoundIndex(fieldset);
    const ape = Math.max(
      1,
      parseInt(fieldset.querySelector(".arrows-per-end-input")?.value || "3", 10)
    );
    const numEnds = Math.max(
      1,
      parseInt(fieldset.querySelector(".num-ends-input")?.value || "1", 10)
    );
    const existing = preserveValues ? serializeArrowString(fieldset) : "";
    const wrap = fieldset.querySelector(".practice-arrow-grid-wrap");
    if (!wrap) return;

    let thead = "<tr><th>End</th>";
    for (let a = 0; a < ape; a++) thead += "<th>Arrow " + (a + 1) + "</th>";
    thead += "<th>End total</th><th>Running</th></tr>";

    let tbody = "";
    for (let e = 0; e < numEnds; e++) {
      tbody += '<tr data-end="' + e + '"><td>' + (e + 1) + "</td>";
      for (let a = 0; a < ape; a++) {
        const pos = e * ape + a;
        const ch = existing[pos] || "";
        tbody +=
          '<td><input type="text" name="arrow_' +
          idx +
          "_" +
          e +
          "_" +
          a +
          '" maxlength="2" class="arrow-cell-input" value="' +
          ch +
          '" placeholder="—"></td>';
      }
      tbody +=
        '<td class="end-total-cell">—</td><td class="running-total-cell">—</td></tr>';
    }

    wrap.innerHTML =
      '<table class="practice-arrow-grid"><thead>' +
      thead +
      '</thead><tbody class="practice-arrow-grid-body">' +
      tbody +
      '</tbody><tfoot><tr><td colspan="' +
      (ape + 1) +
      '"><strong>Round total</strong></td><td colspan="2" class="round-grid-total">—</td></tr></tfoot></table>';

    wrap.querySelectorAll(".arrow-cell-input").forEach((inp) => {
      inp.addEventListener("input", () => updateArrowGridTotals(fieldset));
    });
    updateArrowGridTotals(fieldset);
  }

  function toggleEntryMode(fieldset) {
    const mode = getEntryMode(fieldset);
    const totalPanel = fieldset.querySelector(".practice-total-panel");
    const arrowsPanel = fieldset.querySelector(".practice-arrows-panel");
    if (totalPanel) totalPanel.hidden = mode === "arrows";
    if (arrowsPanel) arrowsPanel.hidden = mode !== "arrows";
    if (mode === "arrows") buildArrowGrid(fieldset, true);
    updatePracticeSummary();
  }

  function reindexRounds() {
    const rounds = roundsContainer.querySelectorAll(".practice-round");
    rounds.forEach((fieldset, displayIndex) => {
      const oldIdx = fieldset.dataset.roundIndex;
      fieldset.dataset.roundIndex = String(displayIndex);
      const legend = fieldset.querySelector("legend");
      if (legend) legend.textContent = "Round " + (displayIndex + 1);
      fieldset.querySelectorAll("[name]").forEach((input) => {
        if (input.name.startsWith("arrow_" + oldIdx + "_")) {
          input.name = input.name.replace(
            "arrow_" + oldIdx + "_",
            "arrow_" + displayIndex + "_"
          );
        } else {
          const m = input.name.match(/^(\w+)_\d+$/);
          if (m) input.name = m[1] + "_" + displayIndex;
        }
      });
      const removeBtn = fieldset.querySelector(".practice-remove-round");
      if (removeBtn) removeBtn.hidden = rounds.length <= 1;
    });
    updatePracticeSummary();
  }

  function bindRound(fieldset) {
    fieldset.querySelectorAll(".entry-mode-radio").forEach((radio) => {
      radio.addEventListener("change", () => toggleEntryMode(fieldset));
    });
    const totalInput = fieldset.querySelector(".round-total-input");
    if (totalInput) {
      totalInput.addEventListener("input", updatePracticeSummary);
    }
    const buildBtn = fieldset.querySelector(".practice-build-grid");
    if (buildBtn) {
      buildBtn.addEventListener("click", () => buildArrowGrid(fieldset, true));
    }
    fieldset.querySelectorAll(".arrow-cell-input").forEach((inp) => {
      inp.addEventListener("input", () => updateArrowGridTotals(fieldset));
    });
    const removeBtn = fieldset.querySelector(".practice-remove-round");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        if (roundsContainer.querySelectorAll(".practice-round").length <= 1) return;
        fieldset.remove();
        reindexRounds();
      });
    }
    toggleEntryMode(fieldset);
  }

  function createRoundFieldset(index) {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "practice-round";
    fieldset.dataset.roundIndex = String(index);
    fieldset.innerHTML =
      "<legend>Round " +
      (index + 1) +
      '</legend><input type="hidden" name="round_index_' +
      index +
      '" value="' +
      index +
      '"><input type="hidden" name="arrow_string_' +
      index +
      '" class="arrow-string-hidden" value="">' +
      '<div class="metadata-row"><label class="metadata-field"><span class="metadata-label">Dist.</span>' +
      '<input type="text" name="distance_' +
      index +
      '" maxlength="12" placeholder="18m"></label>' +
      '<label class="metadata-field"><span class="metadata-label">Cond.</span>' +
      '<input type="text" name="conditions_' +
      index +
      '" maxlength="24" placeholder="indoor"></label></div>' +
      '<div class="practice-entry-mode">' +
      '<label><input type="radio" name="entry_mode_' +
      index +
      '" value="total" checked class="entry-mode-radio"> Round total</label>' +
      '<label><input type="radio" name="entry_mode_' +
      index +
      '" value="arrows" class="entry-mode-radio"> Individual arrows</label></div>' +
      '<div class="practice-total-panel"><label class="practice-total-field">Round total ' +
      '<input type="number" name="total_score_' +
      index +
      '" min="0" class="round-total-input"></label></div>' +
      '<div class="practice-arrows-panel" hidden>' +
      '<div class="practice-arrows-config">' +
      '<label>Arrows per end <input type="number" name="arrows_per_end_' +
      index +
      '" min="1" max="12" class="arrows-per-end-input" value="3"></label>' +
      '<label>Number of ends <input type="number" name="num_ends_' +
      index +
      '" min="1" max="50" class="num-ends-input" value="1"></label>' +
      '<button type="button" class="btn btn-small practice-build-grid">Update scorecard</button></div>' +
      '<div class="practice-arrow-grid-wrap"></div>' +
      '<p class="muted small">Enter one character per arrow (X, T, 9–0, etc.).</p></div>' +
      '<button type="button" class="btn btn-small btn-danger practice-remove-round">Remove round</button>';
    return fieldset;
  }

  roundsContainer.querySelectorAll(".practice-round").forEach((fs) => {
    bindRound(fs);
    if (getEntryMode(fs) === "arrows") updateArrowGridTotals(fs);
  });
  reindexRounds();

  addBtn.addEventListener("click", () => {
    const idx = roundsContainer.querySelectorAll(".practice-round").length;
    const fieldset = createRoundFieldset(idx);
    roundsContainer.appendChild(fieldset);
    bindRound(fieldset);
    reindexRounds();
  });

  if (form) {
    form.addEventListener("submit", () => {
      roundsContainer.querySelectorAll(".practice-round").forEach((fs) => {
        if (getEntryMode(fs) === "arrows") serializeArrowString(fs);
      });
      reindexRounds();
    });
  }
})();
