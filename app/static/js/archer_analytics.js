(function () {
  const data = window.__archerChartData;
  if (!data || typeof Chart === "undefined") return;

  const colors = [
    "#1565c0",
    "#2e7d32",
    "#c62828",
    "#6a1b9a",
    "#ef6c00",
    "#00838f",
  ];

  function makeLineChart(canvasId, labels, datasets, yLabel, dualAxis) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const scales = {
      y: { title: { display: !!yLabel, text: yLabel || "" }, position: "left" },
    };
    if (dualAxis) {
      scales.y1 = {
        type: "linear",
        position: "right",
        title: { display: true, text: "Flier rate %" },
        grid: { drawOnChartArea: false },
      };
    }
    new Chart(el, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        scales,
      },
    });
  }

  const scores = data.scores_by_distance || { labels: {}, values: {} };
  const scoreDatasets = Object.keys(scores.values || {}).map((dist, i) => ({
    label: dist,
    data: scores.values[dist],
    borderColor: colors[i % colors.length],
    tension: 0.2,
  }));
  const scoreLabels =
    Object.values(scores.labels || {})[0] ||
    (data.normalized && data.normalized.labels) ||
    [];
  if (scoreDatasets.length) {
    makeLineChart("chart-scores", scoreLabels, scoreDatasets, "Score");
  }

  const norm = data.normalized || {};
  if (norm.values && norm.values.length) {
    makeLineChart(
      "chart-normalized",
      norm.labels,
      [
        {
          label: "% of max score",
          data: norm.values,
          borderColor: colors[0],
          tension: 0.2,
        },
      ],
      "%"
    );
  }

  const cons = data.consistency || {};
  if (cons.spread && cons.spread.length) {
    makeLineChart(
      "chart-consistency",
      cons.labels,
      [
        {
          label: "Avg end spread",
          data: cons.spread,
          borderColor: colors[1],
          yAxisID: "y",
        },
        {
          label: "Flier rate %",
          data: cons.fliers,
          borderColor: colors[2],
          yAxisID: "y1",
        },
      ],
      "Spread",
      true
    );
  }

  const elim = data.elimination || {};
  if (elim.win_rates && elim.win_rates.length) {
    const el = document.getElementById("chart-elimination");
    if (el) {
      new Chart(el, {
        type: "bar",
        data: {
          labels: elim.labels,
          datasets: [
            {
              label: "Win rate %",
              data: elim.win_rates,
              backgroundColor: colors[0],
            },
            {
              label: "Avg match arrows",
              data: elim.avg_arrows,
              backgroundColor: colors[3],
            },
          ],
        },
        options: { responsive: true },
      });
    }
    const tbody = document.getElementById("elim-seed-body");
    if (tbody && elim.details) {
      elim.details.forEach((row, i) => {
        const vsH = elim.vs_higher[i] || { wins: 0, total: 0 };
        const vsL = elim.vs_lower[i] || { wins: 0, total: 0 };
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          escapeHtml(row.round_name) +
          "</td><td>" +
          escapeHtml(row.event_name) +
          "</td><td>" +
          row.wins +
          "–" +
          row.losses +
          "</td><td>" +
          vsH.wins +
          "/" +
          vsH.total +
          "</td><td>" +
          vsL.wins +
          "/" +
          vsL.total +
          "</td>";
        tbody.appendChild(tr);
      });
    }
  }

  function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text || "";
    return d.innerHTML;
  }

  document.querySelectorAll(".analytics-tabs .tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".analytics-tabs .tab-btn")
        .forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = document.getElementById("tab-" + btn.dataset.tab);
      if (panel) panel.classList.add("active");
    });
  });
})();
