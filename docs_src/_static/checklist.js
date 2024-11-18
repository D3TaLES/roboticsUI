document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("input[type=checkbox]").forEach((checkbox) => {
    checkbox.addEventListener("click", (event) => {
      alert("Item " + (event.target.checked ? "completed" : "unchecked") + "!");
    });
  });
});
