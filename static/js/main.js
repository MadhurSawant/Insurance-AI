/**
 * main.js - Sidebar, navigation, toast, loading, presentation flow
 */

// ═══ SIDEBAR ═════════════════════════════════════════════════════════════════

const sidebar        = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const hamburgerBtn   = document.getElementById("hamburgerBtn");
const sidebarClose   = document.getElementById("sidebarClose");

function openSidebar() {
  sidebar?.classList.add("open");
  sidebarOverlay?.classList.add("active");
}
function closeSidebar() {
  sidebar?.classList.remove("open");
  sidebarOverlay?.classList.remove("active");
}

hamburgerBtn?.addEventListener("click", openSidebar);
sidebarClose?.addEventListener("click", closeSidebar);
sidebarOverlay?.addEventListener("click", closeSidebar);

// ═══ BOOTSTRAP TOOLTIPS ══════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipEls.forEach(el => new bootstrap.Tooltip(el));
  }
});

// ═══ TOAST ════════════════════════════════════════════════════════════════════

function showToast(message, type = "info", duration = 3500) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const icons = { success: "bi-check-circle-fill", error: "bi-x-circle-fill", info: "bi-info-circle-fill" };
  const colors = { success: "#16796f", error: "#e53e3e", info: "#4f81b7" };

  const toast = document.createElement("div");
  toast.className = `toast-item ${type}`;
  toast.innerHTML = `
    <i class="bi ${icons[type] || icons.info}" style="color:${colors[type]};font-size:18px;flex-shrink:0;"></i>
    <span style="flex:1;">${message}</span>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;color:#8da0b5;font-size:16px;">
      <i class="bi bi-x"></i>
    </button>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideInRight 0.3s ease reverse";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ═══ LOADING OVERLAY ═════════════════════════════════════════════════════════

function showLoading(text = "Analyzing customer profile…", callback, delay = 1500) {
  const overlay   = document.getElementById("loadingOverlay");
  const textEl    = document.getElementById("loadingText");
  const ls1 = document.getElementById("ls1");
  const ls2 = document.getElementById("ls2");
  const ls3 = document.getElementById("ls3");

  if (!overlay) return callback && callback();

  if (textEl) textEl.textContent = text;
  overlay.classList.add("active");

  if (ls1 && ls2 && ls3) {
    ls1.classList.add("active");
    ls2.classList.remove("active");
    ls3.classList.remove("active");
    setTimeout(() => { ls1.classList.remove("active"); ls2.classList.add("active"); }, delay * 0.4);
    setTimeout(() => { ls2.classList.remove("active"); ls3.classList.add("active"); }, delay * 0.75);
  }

  setTimeout(() => {
    overlay.classList.remove("active");
    if (callback) callback();
  }, delay);
}

// ═══ SEARCH (DEMO) ════════════════════════════════════════════════════════════

document.getElementById("headerSearch")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const val = e.target.value.trim();
    if (val) {
      showToast(`Searching for "${val}"… (demo)`, "info");
      e.target.value = "";
    }
  }
});

// ═══ ANIMATE ON SCROLL ═══════════════════════════════════════════════════════

function animateOnScroll() {
  const els = document.querySelectorAll(".kpi-card, .chart-card, .feature-card, .model-card, .tech-card, .concept-card");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
      }
    });
  }, { threshold: 0.1 });

  els.forEach(el => {
    el.style.opacity = "0";
    el.style.transform = "translateY(16px)";
    el.style.transition = "opacity 0.5s ease, transform 0.5s ease";
    observer.observe(el);
  });
}

document.addEventListener("DOMContentLoaded", animateOnScroll);

// ═══ IMPACT BAR ANIMATION ════════════════════════════════════════════════════

function animateImpactBars() {
  const bars = document.querySelectorAll(".impact-bar-fill");
  bars.forEach(bar => {
    const target = bar.getAttribute("data-width") || bar.style.width;
    bar.style.width = "0";
    setTimeout(() => { bar.style.width = target; }, 400);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(animateImpactBars, 300);
});
