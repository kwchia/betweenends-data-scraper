(function () {
  const container = document.querySelector("[data-tabs]");
  if (!container) return;

  const tabs = container.querySelectorAll(".tab");
  const panels = container.querySelectorAll(".tab-panel");

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      const target = tab.dataset.tab;
      tabs.forEach(function (t) { t.classList.remove("active"); });
      panels.forEach(function (p) { p.classList.remove("active"); });
      tab.classList.add("active");
      const panel = document.getElementById(target);
      if (panel) panel.classList.add("active");
    });
  });
})();
