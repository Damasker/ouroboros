/* Live server default — static export overwrites / extends this. */
(function () {
  const params = new URLSearchParams(location.search);
  const forced = params.get("mode");
  window.OUROBOROS = {
    mode: forced === "static" ? "static" : "live",
    dataBase: "/data",
    domain: location.host,
  };
})();
