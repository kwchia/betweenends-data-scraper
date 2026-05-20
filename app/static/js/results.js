(function () {
  var LOADING_MESSAGE = "Compiling results… this may take a minute.";

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
    overlay.innerHTML = "<p>" + LOADING_MESSAGE + "</p>";
    document.body.appendChild(overlay);
  }

  var refresh = document.getElementById("refresh-results");
  if (refresh) {
    refresh.addEventListener("click", function () {
      showLoading();
    });
  }

  var clubSwitcher = document.querySelector(".club-switcher");
  if (clubSwitcher) {
    clubSwitcher.addEventListener("submit", function () {
      showLoading();
    });
  }

  var pdfLink = document.getElementById("export-pdf");
  if (pdfLink) {
    pdfLink.addEventListener("click", function () {
      showLoading();
    });
  }
})();
