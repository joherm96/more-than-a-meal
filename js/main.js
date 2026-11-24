/* ==========================================================================
   More Than a Meal — main.js
   Load it in the <head> of every page:  <script src="js/main.js"></script>
   It does two small things:
     1. Opens and closes the mobile menu (the hamburger button).
     2. On book.html, a link like book.html?class=Knife+Skills+101
        pre-selects that class in the "Class" dropdown.
   ========================================================================== */

// Tell the CSS that JavaScript is running (hides the mobile menu until tapped).
document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", function () {
  setUpMenu();
  preselectClass();
});


/* --- 1. Mobile menu -------------------------------------------------------
   Needs: <button class="nav-toggle" aria-expanded="false" aria-controls="site-nav">
          <nav class="nav" id="site-nav">                                       */

function setUpMenu() {
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".nav");
  if (!toggle || !nav) return;

  function setOpen(open) {
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    nav.classList.toggle("is-open", open);
  }

  setOpen(false);

  toggle.addEventListener("click", function () {
    setOpen(toggle.getAttribute("aria-expanded") !== "true");
  });

  // Close after choosing a link (useful for links to #sections on the same page)
  nav.addEventListener("click", function (event) {
    if (event.target.closest("a")) setOpen(false);
  });

  // Close with the Escape key and put focus back on the button
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      setOpen(false);
      toggle.focus();
    }
  });

  // Close when tapping anywhere outside the header
  document.addEventListener("click", function (event) {
    if (nav.classList.contains("is-open") && !event.target.closest(".site-header")) {
      setOpen(false);
    }
  });

  // Reset if the screen gets wide enough to show the full nav (720px)
  var wide = window.matchMedia("(min-width: 45em)");
  var onChange = function () { if (wide.matches) setOpen(false); };
  if (wide.addEventListener) wide.addEventListener("change", onChange);
  else if (wide.addListener) wide.addListener(onChange);
}


/* --- 2. Pre-select a class on the booking form ----------------------------
   Needs: <select id="class"> on book.html.
   book.html?class=Knife+Skills+101 selects the option "Knife Skills 101".
   If no option matches, one is added so the choice is never lost.          */

function preselectClass() {
  var select = document.querySelector("select#class");
  if (!select) return;

  var wanted = new URLSearchParams(window.location.search).get("class");
  if (!wanted) return;
  wanted = wanted.trim();
  if (!wanted) return;

  var normalise = function (text) {
    return text.trim().replace(/\s+/g, " ").toLowerCase();
  };

  var match = null;
  for (var i = 0; i < select.options.length; i++) {
    var option = select.options[i];
    if (normalise(option.value) === normalise(wanted) ||
        normalise(option.textContent) === normalise(wanted)) {
      match = option;
      break;
    }
  }

  if (!match) {
    match = new Option(wanted, wanted);
    select.add(match);
  }

  match.selected = true;
  select.dispatchEvent(new Event("change", { bubbles: true }));
}
