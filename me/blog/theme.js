/* Theme toggle shared by index.html and post.html.
   Dark is the default; the reader's choice is persisted in localStorage.
   A tiny inline <head> snippet (in each page) sets data-theme and the
   highlight.js stylesheet BEFORE first paint to avoid a flash; this file
   wires the button and re-applies on change. post.html additionally listens
   for the "themechange" event to re-render Mermaid diagrams. */
(function () {
	var KEY = "blog-theme";
	var root = document.documentElement;

	function current() {
		try {
			return localStorage.getItem(KEY) || "dark";
		} catch (e) {
			return "dark";
		}
	}

	function apply(theme) {
		root.dataset.theme = theme;

		// Swap the highlight.js stylesheet (both are present; one is disabled).
		var dark = document.getElementById("hljs-dark");
		var light = document.getElementById("hljs-light");
		if (dark && light) {
			dark.disabled = theme !== "dark";
			light.disabled = theme === "dark";
		}

		var btn = document.getElementById("theme-toggle");
		if (btn) {
			btn.textContent = theme === "dark" ? "☀" : "☾"; // ☀ / ☾
			btn.setAttribute(
				"aria-label",
				theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
			);
		}

		document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: theme } }));
	}

	function toggle() {
		var next = current() === "dark" ? "light" : "dark";
		try { localStorage.setItem(KEY, next); } catch (e) { /* private mode */ }
		apply(next);
	}

	// Expose for pages that want the current theme (e.g. Mermaid).
	window.blogTheme = { current: current, apply: apply, toggle: toggle };

	function init() {
		apply(current());
		var btn = document.getElementById("theme-toggle");
		if (btn) btn.addEventListener("click", toggle);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
