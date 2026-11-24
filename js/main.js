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
  setUpBookingEmail();
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


/* --- 3. Booking form: send the request by email ---------------------------
   Needs: <form id="booking-form" data-email="you@example.com"> on book.html.
   On submit, opens the visitor's email app with a message to data-email,
   filled in with every answer from the form.                                */

function setUpBookingEmail() {
  var form = document.getElementById("booking-form");
  if (!form) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!form.reportValidity()) return;
    window.location.href = buildBookingMailto(form);

    var status = document.getElementById("booking-status");
    if (status) {
      status.textContent = "Your email app should be open with your request ready. Hit send and we'll get back to you soon. If nothing opened, email us at " + form.getAttribute("data-email") + ".";
    }
  });
}

function buildBookingMailto(form) {

    var labelFor = function (field) {
      var label = form.querySelector('label[for="' + field.id + '"]');
      if (field.type === "checkbox" && field.name === "group_type") return "Type of group";
      return label ? label.textContent.trim() : field.name;
    };

    var lines = [];
    var groupTypes = [];
    Array.prototype.forEach.call(form.elements, function (field) {
      if (!field.name || field.type === "submit") return;
      if (field.type === "checkbox") {
        if (!field.checked) return;
        if (field.name === "group_type") { groupTypes.push(field.value); return; }
        lines.push(labelFor(field));
        return;
      }
      var value = (field.value || "").trim();
      if (!value) return;
      lines.push(labelFor(field).replace(/\?$/, "") + ": " + value);
    });
    if (groupTypes.length) lines.push("Type of group: " + groupTypes.join(", "));

    var name = (form.elements.name && form.elements.name.value.trim()) || "";
    var subject = "Class booking request" + (name ? " from " + name : "");
    var body = "Hi! I'd like to book a More Than a Meal class.\n\n" + lines.join("\n");

    return "mailto:" + form.getAttribute("data-email") +
      "?subject=" + encodeURIComponent(subject) +
      "&body=" + encodeURIComponent(body);
}
