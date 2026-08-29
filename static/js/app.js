document.addEventListener("DOMContentLoaded", function () {
  // Mobile top-nav toggle
  var navToggle = document.getElementById("navToggle");
  var navMenu = document.getElementById("navMenu");
  if (navToggle && navMenu) {
    navToggle.addEventListener("click", function () {
      navMenu.classList.toggle("open");
    });
  }

  // Dropdown menus in the top navbar
  var dropdownItems = document.querySelectorAll(".nav-item.dropdown-item");
  dropdownItems.forEach(function (item) {
    var trigger = item.querySelector(".nav-top-link");
    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = item.classList.contains("open");
      dropdownItems.forEach(function (i) { i.classList.remove("open"); });
      if (!isOpen) item.classList.add("open");
    });
  });
  document.addEventListener("click", function () {
    dropdownItems.forEach(function (i) { i.classList.remove("open"); });
  });

  // Simple client-side table search (data-table-search input -> table rows)
  document.querySelectorAll("[data-table-search]").forEach(function (input) {
    var tableId = input.getAttribute("data-table-search");
    var table = document.getElementById(tableId);
    if (!table) return;
    input.addEventListener("input", function () {
      var term = input.value.toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (row) {
        row.style.display = row.textContent.toLowerCase().indexOf(term) > -1 ? "" : "none";
      });
    });
  });

  // Auto-calc total freight = freight + dtn + halting
  var freight = document.getElementById("freight");
  var dtn = document.getElementById("dtn");
  var halting = document.getElementById("halting");
  var totalFreight = document.getElementById("total_freight_preview");
  var accountReceivable = document.getElementById("account_receivable");
  var receivableManuallyEdited = false;
  if (accountReceivable) {
    accountReceivable.addEventListener("input", function () { receivableManuallyEdited = true; });
  }
  function recalcTrip() {
    if (!totalFreight) return;
    var f = parseFloat(freight && freight.value) || 0;
    var d = parseFloat(dtn && dtn.value) || 0;
    var h = parseFloat(halting && halting.value) || 0;
    var total = f + d + h;
    totalFreight.textContent = total.toFixed(2);
    if (accountReceivable && !receivableManuallyEdited) {
      accountReceivable.value = total.toFixed(2);
    }
  }
  [freight, dtn, halting].forEach(function (el) {
    if (el) el.addEventListener("input", recalcTrip);
  });
  recalcTrip();

  // Show "Specify Other Expense" field only when Expense Type = Other (Dashboard quick entry)
  var dashExpenseType = document.getElementById("dash_expense_type");
  var dashOtherGroup = document.getElementById("dash_other_expense_group");
  if (dashExpenseType && dashOtherGroup) {
    var toggleDashOther = function () {
      dashOtherGroup.style.display = dashExpenseType.value === "Other" ? "" : "none";
    };
    dashExpenseType.addEventListener("change", toggleDashOther);
    toggleDashOther();
  }

  // Keep the two "Vehicle" dropdowns (step 1 and Load Assessment) in sync
  var vehicleSelects = document.querySelectorAll(".vehicle-select");
  if (vehicleSelects.length > 1) {
    vehicleSelects.forEach(function (sel) {
      sel.addEventListener("change", function () {
        vehicleSelects.forEach(function (other) {
          if (other !== sel) other.value = sel.value;
        });
      });
    });
  }

  // SRB cheque math preview on payments form
  var srbAmount = document.getElementById("srb_amount_data");
  if (srbAmount) {
    var srb = parseFloat(srbAmount.value) || 0;
    var received80 = srb * 0.8;
    var incomeTax20 = srb * 0.2;
    var net = received80 - incomeTax20;
    var setText = function (id, val) {
      var el = document.getElementById(id);
      if (el) el.textContent = val.toFixed(2);
    };
    setText("preview_received_80", received80);
    setText("preview_income_tax_20", incomeTax20);
    setText("preview_net_srb", net);
    var cheque2 = document.getElementById("cheque2_amount");
    if (cheque2 && !cheque2.value) cheque2.value = net.toFixed(2);
  }

  // Auto-dismiss flash messages
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400);
    }, 5000);
  });
});
