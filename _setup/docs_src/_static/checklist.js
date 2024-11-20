document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("input[type=checkbox]").forEach((checkbox) => {
    // Load saved state
    const state = localStorage.getItem(checkbox.nextSibling.textContent.trim());
    if (state === "true") checkbox.checked = true;

    // Save state on change
    checkbox.addEventListener("change", () => {
      localStorage.setItem(
        checkbox.nextSibling.textContent.trim(),
        checkbox.checked
      );
    });
  });
});
