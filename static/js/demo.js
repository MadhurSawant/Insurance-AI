/**
 * demo.js - Demo data, calculation helpers, and lightweight chart initializers
 * for Insurance AI prototype
 */

const CHART_COLORS = {
  navy:       "#0b306b",
  navyLight:  "#1a4a8a",
  cornflower: "#4f81b7",
  freesia:    "#fdd8a5",
  green:      "#16796f",
  light:      "rgba(79,129,183,0.15)",
};

// ═══ DEMO CALCULATIONS ════════════════════════════════════════════════════════

/**
 * Simple demo premium calculation (NOT real ML).
 * Used purely for interactive demo.
 */
function calcDemoPremium(age, bmi, smoking, children) {
  age      = Number(age)      || 30;
  bmi      = Number(bmi)      || 25;
  children = Number(children) || 0;

  let base    = 8000;
  let ageP    = age * 180;
  let bmiP    = Math.max(0, (bmi - 18.5) * 320);
  let smokeP  = (smoking === "yes" || smoking === "Yes") ? 14000 : 0;
  let childP  = children * 800;

  let premium = Math.round(base + ageP + bmiP + smokeP + childP);
  let lower   = Math.round(premium * 0.865);
  let upper   = Math.round(premium * 1.163);

  return { premium, lower, upper, range_width: upper - lower };
}

/**
 * Format number as Indian Rupee string.
 */
function formatINR(amount) {
  return "₹" + Number(amount).toLocaleString("en-IN");
}

// ═══ CHART INITIALIZERS FOR EXPLAIN & WHAT-IF ═════════════════════════════════

function initShapWaterfallChart() {
  const el = document.getElementById("shapWaterfallChart");
  if (!el || typeof Chart === 'undefined') return;
  new Chart(el, {
    type: "bar",
    data: {
      labels: ["Base Value", "Smoker (+)", "BMI (+)", "Age (+)", "Children (+)", "Region (-)", "Final Premium"],
      datasets: [{
        label: "Contribution (₹)",
        data: [8430, 14200, 4850, 2100, 850, -630, 24850],
        backgroundColor: [
          "#8da0b5", CHART_COLORS.navy, CHART_COLORS.navyLight,
          CHART_COLORS.cornflower, "#7aa8d4", CHART_COLORS.green, CHART_COLORS.navy
        ],
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` Contribution: ${ctx.raw >= 0 ? "+" : ""}₹${ctx.raw.toLocaleString("en-IN")}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          ticks: { callback: v => "₹" + (v/1000).toFixed(0) + "K" },
          grid: { color: "rgba(0,0,0,0.04)" },
        },
      },
    },
  });
}

function initWhatIfChart() {
  const el = document.getElementById("whatifChart");
  if (!el || typeof Chart === 'undefined') return;
  window.whatifChart = new Chart(el, {
    type: "bar",
    data: {
      labels: ["Original Profile (Baseline)", "Scenario Profile"],
      datasets: [{
        label: "Estimated Premium (₹)",
        data: [24850, 24850],
        backgroundColor: [CHART_COLORS.navy, CHART_COLORS.green],
        borderRadius: 8,
        borderSkipped: false,
        barThickness: 50,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` Premium: ₹${ctx.raw.toLocaleString("en-IN")}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          ticks: { callback: v => "₹" + (v/1000).toFixed(0) + "K" },
          grid: { color: "rgba(0,0,0,0.04)" },
        },
      },
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initShapWaterfallChart();
  initWhatIfChart();
});
