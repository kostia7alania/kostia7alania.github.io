const root = document.documentElement;
const themeControl = document.querySelector("[data-theme-control]");
const themeSelect = document.querySelector("[data-theme-select]");
const colorScheme = document.querySelector('meta[name="color-scheme"]');

themeSelect.value = root.dataset.theme || "system";
themeControl.hidden = false;

themeSelect.addEventListener("change", () => {
  const preference = themeSelect.value;
  if (preference === "system") {
    delete root.dataset.theme;
  } else {
    root.dataset.theme = preference;
  }
  colorScheme.content = preference === "system" ? "dark light" : preference;
  try {
    localStorage.setItem("kostia-theme", preference);
  } catch {
    // The current page still reflects the choice.
  }
});

const toolbar = document.querySelector("[data-project-toolbar]");

if (toolbar) {
  const projects = [...document.querySelectorAll("[data-project]")];
  const buttons = [...toolbar.querySelectorAll("[data-filter]")];
  const countLabel = toolbar.querySelector("[data-project-count]");

  function showProjects(filter) {
    let visible = 0;
    for (const project of projects) {
      project.hidden = filter !== "all" && project.dataset.project !== filter;
      if (!project.hidden) visible += 1;
    }
    for (const button of buttons) {
      button.setAttribute("aria-pressed", String(button.dataset.filter === filter));
    }
    countLabel.textContent = root.lang === "ru"
      ? `Показано ${visible} из ${projects.length}`
      : `Showing ${visible} of ${projects.length}`;
  }

  toolbar.addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter]");
    if (button) showProjects(button.dataset.filter);
  });
  showProjects("all");
  toolbar.hidden = false;
}
