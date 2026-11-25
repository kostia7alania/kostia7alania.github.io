(() => {
  try {
    const preference = localStorage.getItem("kostia-theme");
    if (preference === "light" || preference === "dark") {
      document.documentElement.dataset.theme = preference;
      document.querySelector('meta[name="color-scheme"]').content = preference;
    }
  } catch {
    // The system theme also works when local storage is unavailable.
  }
})();
