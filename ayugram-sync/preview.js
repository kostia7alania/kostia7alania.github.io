(() => {
  if (!navigator.clipboard?.writeText) return;

  const russian = document.documentElement.lang === "ru";
  const copied = russian ? "Скопировано" : "Copied";
  const copyManually = russian ? "Скопируй выделенный текст" : "Copy the selected text manually";
  const timers = new WeakMap();
  let previous = "";

  async function copy(button, target) {
    const status = button.nextElementSibling;
    clearTimeout(timers.get(button));
    let message = copied;

    try {
      await navigator.clipboard.writeText(target.textContent.trim());
    } catch {
      window.getSelection()?.selectAllChildren(target);
      message = copyManually;
    }

    status.textContent = message === previous ? message + "\u00a0" : message;
    previous = status.textContent;
    timers.set(button, setTimeout(() => {
      status.textContent = "";
    }, 2400));
  }

  const buttons = document.querySelectorAll(".sync-copy-button");
  buttons.forEach((button) => { button.hidden = false; });

  if ("CommandEvent" in window) {
    document.addEventListener("command", (event) => {
      if (event.command === "--copy-snippet" && event.source?.classList.contains("sync-copy-button")) {
        copy(event.source, event.target);
      }
    }, true);
  } else {
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const target = document.getElementById(button.getAttribute("commandfor"));
        if (target) copy(button, target);
      });
    });
  }
})();
