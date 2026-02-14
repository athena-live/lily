(function () {
  const root = document.documentElement;
  const body = document.body;
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const themeLabel = document.querySelector("[data-theme-label]");

  if (!root) return;

  const themeEndpoint = body ? body.dataset.themeEndpoint : null;
  const isAuthed = body && body.dataset.auth === "1";

  const applyTheme = (theme, { persist } = { persist: false }) => {
    root.setAttribute("data-theme", theme);
    if (themeLabel) {
      themeLabel.textContent = theme === "dark" ? "Dark mode" : "Light mode";
    }
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", theme === "dark");
    }

    if (persist) {
      try {
        localStorage.setItem("theme", theme);
      } catch (e) {
        // Ignore storage errors.
      }
      if (isAuthed && themeEndpoint) {
        const getCookie = (name) => {
          const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
          return match ? decodeURIComponent(match[2]) : "";
        };
        fetch(themeEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          credentials: "same-origin",
          body: JSON.stringify({ theme }),
        }).catch(() => undefined);
      }
    }
  };

  let initialTheme = root.getAttribute("data-theme") || "light";
  try {
    const storedTheme = localStorage.getItem("theme");
    if (storedTheme === "dark" || storedTheme === "light") {
      initialTheme = storedTheme;
    }
  } catch (e) {
    // Ignore storage errors.
  }

  applyTheme(initialTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(nextTheme, { persist: true });
    });
  }
})();
