let currentTab = 'dashboard';
let cashflowChartInstance = null;
let categoryChartInstance = null;
let activeDealsCache = [];
let activeAccountsCache = [];
let searchTimeout = null;


let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setDefaultDates();
  checkAuth(); // check login status first
});



async function checkAuth() {
  try {
    const res = await fetch('/api/me', { credentials: 'include' });
    if (res.ok) {
      const user = await res.json();
      currentUser = user;
      document.getElementById('auth-overlay').classList.add('hidden');
      document.getElementById('app-container').classList.remove('hidden');
      loadAllData();
    } else {
      document.getElementById('auth-overlay').classList.remove('hidden');
      document.getElementById('app-container').classList.add('hidden');
    }
  } catch (e) {
    document.getElementById('auth-overlay').classList.remove('hidden');
    document.getElementById('app-container').classList.add('hidden');
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'include'
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Logged in successfully!');
      checkAuth();
    } else {
      showToast(data.error || 'Login failed', 'error');
    }
  } catch (err) {
    showToast('Error logging in', 'error');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const username = document.getElementById('register-username').value;
  const password = document.getElementById('register-password').value;
  try {
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'include'
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Account created! Please log in.');
      showLogin();
    } else {
      showToast(data.error || 'Registration failed', 'error');
    }
  } catch (err) {
    showToast('Error registering', 'error');
  }
}

async function handleLogout() {
  await fetch('/api/logout', { method: 'POST', credentials: 'include' });
  currentUser = null;
  document.getElementById('auth-overlay').classList.remove('hidden');
  document.getElementById('app-container').classList.add('hidden');
  showToast('Logged out');
}

function showRegister() {
  document.getElementById('auth-form-container').classList.add('hidden');
  document.getElementById('register-form-container').classList.remove('hidden');
}

function showLogin() {
  document.getElementById('register-form-container').classList.add('hidden');
  document.getElementById('auth-form-container').classList.remove('hidden');
}

function setDefaultDates() {
  const today = new Date().toISOString().split('T')[0];
  const txDate = document.getElementById('tx-date');
  if (txDate) txDate.value = today;
}

function initTheme() {
  const savedTheme = localStorage.getItem('bouncy_theme') || 'light';
  if (savedTheme === 'light') {
    document.documentElement.classList.remove('dark');
    updateThemeIcon('light');
  } else {
    document.documentElement.classList.add('dark');
    updateThemeIcon('dark');
  }
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('bouncy_theme', isDark ? 'dark' : 'light');
  updateThemeIcon(isDark ? 'dark' : 'light');
  if (cashflowChartInstance) refreshCharts();
}

function updateThemeIcon(mode) {
  const btn = document.getElementById('theme-btn');
  if (!btn) return;
  if (mode === 'light') {
    btn.innerHTML = '<i class="ph ph-moon text-lg text-indigo-600"></i>';
  } else {
    btn.innerHTML = '<i class="ph ph-sun text-lg text-amber-400"></i>';
  }
}

function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    if (btn.dataset.tab === tabName) {
      btn.className = 'tab-btn bounce-btn px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all active-tab bg-brand-500 text-white shadow-lg shadow-brand-500/30';
    } else {
      btn.className = 'tab-btn bounce-btn px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all';
    }
  });
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  const activeContent = document.getElementById(`tab-${tabName}`);
  if (activeContent) {
    activeContent.classList.remove('hidden');
    activeContent.classList.add('anim-slide-up');
  }
  if (tabName === 'dashboard') loadSummary();
  if (tabName === 'accounts') loadAccounts();
  if (tabName === 'logger') loadTransactions();
  if (tabName === 'deals') loadDeals();
  if (tabName === 'budgets') { loadBudgets(); loadGoals(); }
  if (tabName === 'analytics') loadAnalytics();
}

async function loadAllData() {
  await Promise.all([
    loadSummary(),
    loadAccounts(),
    loadTransactions(),
    loadDeals(),
    loadBudgets(),
    loadGoals()
  ]);
}

async function loadSummary() {
  try {
    const res = await fetch('/api/summary', { credentials: 'include' });
    const data = await res.json();
    animateValue('kpi-net-balance', data.net_balance, '₱');
    animateValue('kpi-income', data.total_income, '₱');
    animateValue('kpi-expense', data.total_expense, '₱');
    animateValue('kpi-deals', data.deal_savings, '₱');
    animateValue('kpi-total-on-hand', data.net_balance || 0, '₱');
    const annualInterestEl = document.getElementById('kpi-annual-interest');
    if (annualInterestEl) {
      annualInterestEl.innerText = `+₱${(data.total_annual_interest || 0).toFixed(2)} / yr`;
    }
    const monthlyInterestEl = document.getElementById('kpi-monthly-interest');
    if (monthlyInterestEl) {
      monthlyInterestEl.innerText = `approx. +₱${(data.total_monthly_interest || 0).toFixed(2)} / month`;
    }
    const savingsRateEl = document.getElementById('kpi-savings-rate');
    if (savingsRateEl) {
      savingsRateEl.innerText = `${data.savings_rate}%`;
      savingsRateEl.className = data.savings_rate >= 20
        ? 'px-2 py-0.5 rounded-md font-semibold bg-emerald-500/20 text-emerald-400'
        : 'px-2 py-0.5 rounded-md font-semibold bg-amber-500/20 text-amber-400';
    }
    renderRecentTransactions(data.recent_transactions || []);
    renderCashflowChart(data.monthly_trends || []);
    renderCategoryChart(data.category_breakdown || []);
    loadBudgetMeters();
  } catch (err) {
    console.error('Error loading summary:', err);
  }
}

function animateValue(elementId, targetValue, prefix = '') {
  const el = document.getElementById(elementId);
  if (!el) return;
  const start = 0;
  const end = targetValue;
  const duration = 600;
  const startTime = performance.now();
  function updateNumber(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const current = start + (end - start) * easeProgress;
    el.innerText = `${prefix}${current.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (progress < 1) {
      requestAnimationFrame(updateNumber);
    }
  }
  requestAnimationFrame(updateNumber);
}

function renderRecentTransactions(txs) {
  const container = document.getElementById('dashboard-recent-list');
  if (!container) return;
  if (txs.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 py-3 text-center">No recent transactions. Click "+ Log Transaction" to add one.</div>`;
    return;
  }
  container.innerHTML = txs.map(t => {
    const isIncome = t.type === 'income';
    const amountClass = isIncome ? 'text-emerald-400 font-bold' : 'text-slate-100 font-bold';
    const amountPrefix = isIncome ? '+' : '-';
    const iconClass = isIncome ? 'ph-arrow-down-left text-emerald-400' : 'ph-shopping-bag text-rose-400';
    return `
      <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 hover:bg-slate-800/70 border border-slate-700/40 transition-all bounce-pill">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center">
            <i class="ph ${iconClass} text-lg"></i>
          </div>
          <div>
            <div class="text-sm font-semibold text-white">${escapeHtml(t.description || t.category)}</div>
            <div class="text-xs text-slate-400">${t.date} · <span class="text-slate-500">${t.category}</span></div>
          </div>
        </div>
        <div class="text-right">
          <div class="${amountClass}">${amountPrefix}₱${t.amount.toFixed(2)}</div>
          <div class="text-[10px] text-slate-500">${t.payment_method || 'Cash'}</div>
        </div>
      </div>
    `;
  }).join('');
}

async function loadTransactions() {
  try {
    const search = document.getElementById('tx-search-input')?.value || '';
    const type = document.getElementById('tx-filter-type')?.value || '';
    const category = document.getElementById('tx-filter-category')?.value || '';
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (type) params.append('type', type);
    if (category) params.append('category', category);
    const res = await fetch(`/api/transactions?${params.toString()}`, { credentials: 'include' });
    const data = await res.json();
    const txs = data.transactions || [];
    const tbody = document.getElementById('transactions-table-body');
    const emptyState = document.getElementById('tx-empty-state');
    if (txs.length === 0) {
      tbody.innerHTML = '';
      if (emptyState) emptyState.classList.remove('hidden');
      return;
    }
    if (emptyState) emptyState.classList.add('hidden');
    tbody.innerHTML = txs.map(t => {
      const isIncome = t.type === 'income';
      const badgeColor = isIncome
        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
        : 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      const amountPrefix = isIncome ? '+' : '-';
      const dealBadge = t.deal_title ? `
        <span class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-pink-500/20 text-pink-300 border border-pink-500/30 mt-1">
          <i class="ph ph-tag"></i> Deal: ${escapeHtml(t.deal_title)}
        </span>
      ` : '';
      return `
        <tr class="hover:bg-slate-800/40 transition-colors">
          <td class="px-5 py-3.5 text-xs text-slate-400 whitespace-nowrap">${t.date}</td>
          <td class="px-5 py-3.5">
            <div class="font-semibold text-white">${escapeHtml(t.description || 'No description')}</div>
            ${dealBadge}
            ${t.tags ? `<div class="text-[10px] text-slate-500 mt-0.5">#${escapeHtml(t.tags.split(',').join(' #'))}</div>` : ''}
          </td>
          <td class="px-5 py-3.5 whitespace-nowrap">
            <span class="px-2.5 py-1 rounded-lg text-xs font-semibold border ${badgeColor}">
              ${t.category}
            </span>
          </td>
          <td class="px-5 py-3.5 text-xs text-slate-300 whitespace-nowrap">
            <span class="flex items-center gap-1.5">
              <i class="ph ph-credit-card text-slate-400"></i> ${t.payment_method || 'Cash'}
            </span>
          </td>
          <td class="px-5 py-3.5 text-right font-bold ${isIncome ? 'text-emerald-400' : 'text-rose-400'} whitespace-nowrap">
            ${amountPrefix}₱${t.amount.toFixed(2)}
          </td>
          <td class="px-5 py-3.5 text-center whitespace-nowrap">
            <div class="flex items-center justify-center gap-2">
              <button onclick="editTransaction(${JSON.stringify(t).replace(/"/g, '&quot;')})" class="bounce-btn w-8 h-8 rounded-lg bg-slate-800 hover:bg-brand-500/20 text-slate-400 hover:text-brand-400 flex items-center justify-center" title="Edit">
                <i class="ph ph-pencil-simple"></i>
              </button>
              <button onclick="deleteTransaction(${t.id})" class="bounce-btn w-8 h-8 rounded-lg bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 flex items-center justify-center" title="Delete">
                <i class="ph ph-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
    populateCategoryFilter(txs);
  } catch (err) {
    console.error('Error loading transactions:', err);
  }
}

function debounceSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(loadTransactions, 300);
}

function populateCategoryFilter(txs) {
  const catSelect = document.getElementById('tx-filter-category');
  if (!catSelect) return;
  const currentVal = catSelect.value;
  const categories = Array.from(new Set(txs.map(t => t.category))).filter(Boolean);
  let html = '<option value="">All Categories</option>';
  categories.forEach(c => {
    html += `<option value="${escapeHtml(c)}" ${c === currentVal ? 'selected' : ''}>${escapeHtml(c)}</option>`;
  });
  catSelect.innerHTML = html;
}

async function loadDeals(status = '') {
  try {
    const url = status && status !== 'all' ? `/api/deals?status=${status}` : '/api/deals';
    const res = await fetch(url, { credentials: 'include' });
    const data = await res.json();
    const deals = data.deals || [];
    activeDealsCache = deals;
    const activeCount = deals.filter(d => d.status === 'active' || d.status === 'wishlist').length;
    const badge = document.getElementById('deals-count-badge');
    if (badge) badge.innerText = activeCount;
    const totalSaved = deals.filter(d => d.status === 'purchased' || d.status === 'active').reduce((acc, d) => acc + (d.amount_saved || 0), 0);
    const heroSaved = document.getElementById('deals-hero-saved');
    if (heroSaved) heroSaved.innerText = `₱${totalSaved.toFixed(2)}`;
    populateDealsInTxModal(deals);
    const container = document.getElementById('deals-grid');
    if (!container) return;
    if (deals.length === 0) {
      container.innerHTML = `
        <div class="col-span-full p-8 text-center glass-card rounded-2xl">
          <i class="ph ph-tag-chevron text-4xl text-pink-500 mb-2 anim-rubber"></i>
          <h4 class="font-bold text-white">No Deals Logged Yet</h4>
          <p class="text-xs text-slate-400 mt-1">Found a sale, discount code, or price drop? Log it here to track your savings!</p>
          <button onclick="openDealModal()" class="bounce-btn mt-4 px-4 py-2 bg-pink-500 hover:bg-pink-600 text-white text-xs font-bold rounded-xl shadow-lg shadow-pink-500/20">
            + Log Your First Deal
          </button>
        </div>
      `;
      return;
    }
    container.innerHTML = deals.map(d => {
      const discountPct = d.original_price > 0 ? Math.round(((d.original_price - d.deal_price) / d.original_price) * 100) : 0;
      let statusBadge = '';
      if (d.status === 'active') {
        statusBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-pink-500/20 text-pink-400 border border-pink-500/30">🔥 Active Deal</span>';
      } else if (d.status === 'wishlist') {
        statusBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">⭐ Wishlist</span>';
      } else if (d.status === 'purchased') {
        statusBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">✅ Claimed</span>';
      } else {
        statusBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-700 text-slate-400">⌛ Expired</span>';
      }
      return `
        <div class="glass-card bounce-card p-5 rounded-2xl flex flex-col justify-between border-slate-700/60 relative overflow-hidden group">
          <div class="absolute top-0 right-0 w-20 h-20 bg-pink-500/10 rounded-bl-full pointer-events-none"></div>
          <div class="space-y-3">
            <div class="flex items-start justify-between gap-2">
              ${statusBadge}
              <div class="flex items-center gap-1.5">
                <button onclick="editDeal(${JSON.stringify(d).replace(/"/g, '&quot;')})" class="w-7 h-7 rounded-lg bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center">
                  <i class="ph ph-pencil-simple text-xs"></i>
                </button>
                <button onclick="deleteDeal(${d.id})" class="w-7 h-7 rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 flex items-center justify-center">
                  <i class="ph ph-trash text-xs"></i>
                </button>
              </div>
            </div>
            <div>
              <h4 class="font-bold text-white text-base leading-snug">${escapeHtml(d.title)}</h4>
              <div class="text-xs text-slate-400 flex items-center gap-2 mt-1">
                <span><i class="ph ph-storefront"></i> ${escapeHtml(d.store || 'Online / Retail')}</span>
                <span>•</span>
                <span>${escapeHtml(d.category || 'Shopping')}</span>
              </div>
            </div>
            <div class="p-3 rounded-xl bg-slate-800/60 border border-slate-700/40 flex items-center justify-between">
              <div>
                <span class="text-[10px] text-slate-400 uppercase font-semibold">Deal Price</span>
                <div class="text-lg font-black text-emerald-400">₱${d.deal_price.toFixed(2)}</div>
              </div>
              <div class="text-right">
                <span class="text-[10px] text-slate-500 line-through">Orig: ₱${d.original_price.toFixed(2)}</span>
                <div class="text-xs font-bold text-pink-400">Save ₱${d.amount_saved.toFixed(2)} (${discountPct}% OFF)</div>
              </div>
            </div>
            ${d.url_or_notes ? `
              <div class="text-xs text-slate-300 bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/30 flex items-start gap-1.5">
                <i class="ph ph-info text-pink-400 mt-0.5"></i>
                <span class="truncate">${escapeHtml(d.url_or_notes)}</span>
              </div>
            ` : ''}
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
            ${d.status !== 'purchased' ? `
              <button onclick="claimDealAsExpense(${d.id})" class="bounce-btn w-full py-2 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-pink-500/20">
                <i class="ph ph-shopping-cart"></i> Buy & Log Expense
              </button>
            ` : `
              <div class="text-xs text-emerald-400 font-bold flex items-center gap-1">
                <i class="ph ph-check-circle"></i> Logged into Expenses
              </div>
            `}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading deals:', err);
  }
}

function filterDeals(status) {
  document.querySelectorAll('.deal-filter-btn').forEach(btn => {
    if (btn.dataset.status === status) {
      btn.className = 'deal-filter-btn bounce-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-pink-500 text-white';
    } else {
      btn.className = 'deal-filter-btn bounce-btn px-3 py-1.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white';
    }
  });
  loadDeals(status);
}

function populateDealsInTxModal(deals) {
  const select = document.getElementById('tx-deal-id');
  if (!select) return;
  let html = '<option value="">-- No Linked Deal --</option>';
  deals.filter(d => d.status !== 'expired').forEach(d => {
    html += `<option value="${d.id}">🏷️ ${escapeHtml(d.title)} (Save ₱${d.amount_saved.toFixed(2)})</option>`;
  });
  select.innerHTML = html;
}

async function loadBudgets() {
  try {
    const res = await fetch('/api/budgets', { credentials: 'include' });
    const data = await res.json();
    const budgets = data.budgets || [];
    renderBudgetMetersFull(budgets);
    renderDashboardBudgetMeters(budgets);
  } catch (err) {
    console.error('Error loading budgets:', err);
  }
}

function renderDashboardBudgetMeters(budgets) {
  const container = document.getElementById('dashboard-budget-meters');
  if (!container) return;
  if (budgets.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 text-center py-2">No category budgets set. Click Manage to set limits.</div>`;
    return;
  }
  container.innerHTML = budgets.slice(0, 4).map(b => {
    const isOver = b.percentage >= 100;
    const isWarning = b.percentage >= 80 && !isOver;
    const barColor = isOver ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-brand-500';
    return `
      <div class="space-y-1.5">
        <div class="flex items-center justify-between text-xs font-semibold">
          <span class="text-slate-200">${escapeHtml(b.category)}</span>
          <span class="${isOver ? 'text-rose-400 font-bold' : 'text-slate-400'}">₱${b.spent.toFixed(0)} / ₱${b.monthly_limit.toFixed(0)}</span>
        </div>
        <div class="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
          <div class="${barColor} h-full rounded-full transition-all duration-500 ease-out" style="width: ${Math.min(b.percentage, 100)}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderBudgetMetersFull(budgets) {
  const container = document.getElementById('budgets-full-grid');
  if (!container) return;
  if (budgets.length === 0) {
    container.innerHTML = `<div class="col-span-full p-6 text-center text-slate-400">No monthly budgets configured. Click "+ Set Budget" above.</div>`;
    return;
  }
  container.innerHTML = budgets.map(b => {
    const isOver = b.percentage >= 100;
    const isWarning = b.percentage >= 80 && !isOver;
    const statusText = isOver ? '⚠️ Over Budget!' : isWarning ? '⚡ Nearing Limit' : '👍 On Track';
    const statusClass = isOver ? 'text-rose-400 bg-rose-500/20' : isWarning ? 'text-amber-400 bg-amber-500/20' : 'text-emerald-400 bg-emerald-500/20';
    const barColor = isOver ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-gradient-to-r from-brand-500 to-indigo-400';
    return `
      <div class="glass-card bounce-card p-5 rounded-2xl space-y-3 border-slate-700/60">
        <div class="flex items-center justify-between">
          <h4 class="font-bold text-white text-base">${escapeHtml(b.category)}</h4>
          <span class="px-2 py-0.5 rounded-md text-xs font-bold ${statusClass}">${statusText}</span>
        </div>
        <div class="flex items-baseline justify-between">
          <div>
            <span class="text-2xl font-black ${isOver ? 'text-rose-400' : 'text-white'}">₱${b.spent.toFixed(2)}</span>
            <span class="text-xs text-slate-400">spent</span>
          </div>
          <div class="text-right">
            <span class="text-xs font-semibold text-slate-300">Cap: ₱${b.monthly_limit.toFixed(2)}</span>
            <div class="text-[11px] text-slate-400">${b.remaining >= 0 ? `₱${b.remaining.toFixed(2)} remaining` : `-₱${Math.abs(b.remaining).toFixed(2)} over limit`}</div>
          </div>
        </div>
        <div class="w-full h-3 bg-slate-800 rounded-full overflow-hidden">
          <div class="${barColor} h-full rounded-full transition-all duration-700 ease-out" style="width: ${Math.min(b.percentage, 100)}%"></div>
        </div>
        <div class="flex items-center justify-between text-xs text-slate-400 pt-1">
          <span>${b.percentage}% used</span>
          <button onclick="deleteBudget(${b.id})" class="text-slate-500 hover:text-rose-400">
            <i class="ph ph-trash"></i> Delete
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function loadGoals() {
  try {
    const res = await fetch('/api/goals', { credentials: 'include' });
    const data = await res.json();
    const goals = data.goals || [];
    const container = document.getElementById('goals-grid');
    if (!container) return;
    if (goals.length === 0) {
      container.innerHTML = `<div class="col-span-full p-6 text-center text-slate-400">No savings targets set yet. Set a goal for a new phone, car, or emergency buffer!</div>`;
      return;
    }
    container.innerHTML = goals.map(g => {
      const pct = g.target_amount > 0 ? Math.min(100, Math.round((g.current_amount / g.target_amount) * 100)) : 0;
      const isComplete = pct >= 100;
      return `
        <div class="glass-card bounce-card p-5 rounded-2xl space-y-4 border-slate-700/60 relative">
          <div class="flex items-start justify-between">
            <div>
              <span class="text-xs font-bold text-emerald-400 flex items-center gap-1"><i class="ph ph-target"></i> ${escapeHtml(g.category || 'Savings')}</span>
              <h4 class="font-bold text-white text-lg mt-0.5">${escapeHtml(g.title)}</h4>
            </div>
            <button onclick="deleteGoal(${g.id})" class="text-slate-500 hover:text-rose-400">
              <i class="ph ph-trash"></i>
            </button>
          </div>
          <div class="flex items-baseline justify-between">
            <span class="text-2xl font-black text-white">₱${g.current_amount.toFixed(2)}</span>
            <span class="text-xs font-bold text-slate-400">Target: ₱${g.target_amount.toFixed(2)}</span>
          </div>
          <div class="w-full h-3 bg-slate-800 rounded-full overflow-hidden">
            <div class="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-700" style="width: ${pct}%"></div>
          </div>
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold ${isComplete ? 'text-emerald-400' : 'text-slate-300'}">${pct}% Achieved</span>
            <button onclick="contributeToGoal(${g.id}, ${g.current_amount})" class="bounce-btn px-2.5 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 rounded-lg font-bold flex items-center gap-1">
              <i class="ph ph-plus"></i> Add Money
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading goals:', err);
  }
}

async function loadAccounts(typeFilter = 'all') {
  try {
    const res = await fetch('/api/accounts', { credentials: 'include' });
    const data = await res.json();
    let accounts = data.accounts || [];
    activeAccountsCache = accounts;
    const badge = document.getElementById('accounts-count-badge');
    if (badge) badge.innerText = accounts.length;
    const totalOnHand = accounts.reduce((acc, a) => acc + (a.balance || 0), 0);
    const totalAnnualInterest = accounts.reduce((acc, a) => acc + (a.annual_interest || (a.balance * ((a.interest_rate_pa || 0) / 100))), 0);
    const totalMonthlyInterest = totalAnnualInterest / 12;
    const onHandEl = document.getElementById('accounts-total-on-hand');
    if (onHandEl) onHandEl.innerText = `₱${totalOnHand.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const interestEl = document.getElementById('accounts-total-interest');
    if (interestEl) interestEl.innerText = `+₱${totalAnnualInterest.toFixed(2)} / yr`;
    if (typeFilter && typeFilter !== 'all') {
      accounts = accounts.filter(a => a.account_type.toLowerCase().includes(typeFilter.toLowerCase()));
    }
    const container = document.getElementById('accounts-grid');
    if (!container) return;
    if (accounts.length === 0) {
      container.innerHTML = `
        <div class="col-span-full p-8 text-center glass-card rounded-2xl">
          <i class="ph ph-bank text-4xl text-blue-400 mb-2 anim-rubber"></i>
          <h4 class="font-bold text-white">No Bank Accounts Logged</h4>
          <p class="text-xs text-slate-400 mt-1">Log your checking, savings, HYSA, or cash in your wallet to track your overall liquid wealth.</p>
          <button onclick="openAccountModal()" class="bounce-btn mt-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/20">
            + Add First Account
          </button>
        </div>
      `;
      return;
    }
    container.innerHTML = accounts.map(a => {
      const rate = a.interest_rate_pa || 0.0;
      const annualInt = a.annual_interest || (a.balance * (rate / 100));
      const monthlyInt = annualInt / 12;
      let typeBadge = '';
      if (a.account_type.includes('Savings')) {
        typeBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">💰 High-Yield Savings</span>';
      } else if (a.account_type.includes('Checking')) {
        typeBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">💳 Checking</span>';
      } else if (a.account_type.includes('Cash')) {
        typeBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">💵 Cash On-Hand</span>';
      } else if (a.account_type.includes('Deposit')) {
        typeBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-pink-500/20 text-pink-400 border border-pink-500/30">🔒 Time Deposit (CD)</span>';
      } else {
        typeBadge = `<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">📱 ${escapeHtml(a.account_type)}</span>`;
      }
      return `
        <div class="glass-card bounce-card p-5 rounded-3xl space-y-4 border-slate-700/60 relative overflow-hidden group">
          <div class="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-bl-full pointer-events-none group-hover:bg-blue-500/20 transition-all"></div>
          <div class="flex items-start justify-between gap-2">
            ${typeBadge}
            <div class="flex items-center gap-1.5">
              <button onclick="editAccount(${JSON.stringify(a).replace(/"/g, '&quot;')})" class="w-7 h-7 rounded-lg bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center">
                <i class="ph ph-pencil-simple text-xs"></i>
              </button>
              <button onclick="deleteAccount(${a.id})" class="w-7 h-7 rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 flex items-center justify-center">
                <i class="ph ph-trash text-xs"></i>
              </button>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-slate-400 flex items-center gap-1">
              <i class="ph ph-buildings"></i> ${escapeHtml(a.institution)}
            </div>
            <h4 class="font-bold text-white text-lg mt-0.5">${escapeHtml(a.name)}</h4>
          </div>
          <div class="p-3.5 rounded-2xl bg-slate-800/80 border border-slate-700/50 flex items-center justify-between">
            <div>
              <span class="text-[10px] text-slate-400 uppercase font-semibold">Current Balance</span>
              <div class="text-2xl font-black text-white">₱${a.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            </div>
            <button onclick="openQuickBalanceModal(${a.id}, ${a.balance}, '${escapeHtml(a.name)}')" class="bounce-btn px-2.5 py-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 rounded-xl text-xs font-bold flex items-center gap-1">
              <i class="ph ph-arrows-clockwise"></i> Update
            </button>
          </div>
          ${rate > 0 ? `
            <div class="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 space-y-1 text-xs">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-emerald-300 flex items-center gap-1">
                  <i class="ph ph-trend-up"></i> Interest Rate:
                </span>
                <span class="font-black text-emerald-400 px-2 py-0.5 bg-emerald-500/20 rounded-md">${rate}% p.a.</span>
              </div>
              <div class="flex items-center justify-between text-[11px] text-slate-300 pt-0.5">
                <span>Annual Yield: <b class="text-emerald-400">+₱${annualInt.toFixed(2)}</b></span>
                <span>(+₱${monthlyInt.toFixed(2)}/mo)</span>
              </div>
            </div>
          ` : `
            <div class="text-[11px] text-slate-500 italic px-1 flex items-center gap-1">
              <i class="ph ph-info"></i> Standard non-interest bearing account
            </div>
          `}
          ${a.notes ? `
            <div class="text-xs text-slate-400 bg-slate-800/30 p-2 rounded-xl border border-slate-700/30 truncate">
              ${escapeHtml(a.notes)}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading accounts:', err);
  }
}

function filterAccounts(type) {
  document.querySelectorAll('.account-filter-btn').forEach(btn => {
    if (btn.dataset.type === type) {
      btn.className = 'account-filter-btn bounce-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-blue-500 text-white';
    } else {
      btn.className = 'account-filter-btn bounce-btn px-3 py-1.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white';
    }
  });
  loadAccounts(type);
}

function calculateAccountInterestPreview() {
  const bal = parseFloat(document.getElementById('account-balance')?.value) || 0;
  const rate = parseFloat(document.getElementById('account-rate-pa')?.value) || 0;
  const annual = bal * (rate / 100.0);
  const monthly = annual / 12.0;
  const preview = document.getElementById('account-interest-preview');
  if (preview) {
    preview.innerText = `+₱${annual.toFixed(2)} / yr (+₱${monthly.toFixed(2)} / mo)`;
  }
}

function openAccountModal() {
  document.getElementById('account-form').reset();
  document.getElementById('account-id').value = '';
  document.getElementById('account-modal-title').innerText = 'Log Bank / Savings Account';
  calculateAccountInterestPreview();
  openModal('modal-account');
}

function editAccount(acc) {
  openAccountModal();
  document.getElementById('account-id').value = acc.id;
  document.getElementById('account-name').value = acc.name;
  document.getElementById('account-institution').value = acc.institution;
  document.getElementById('account-type').value = acc.account_type;
  document.getElementById('account-balance').value = acc.balance;
  document.getElementById('account-rate-pa').value = acc.interest_rate_pa || 0;
  document.getElementById('account-notes').value = acc.notes || '';
  document.getElementById('account-modal-title').innerText = 'Edit Bank Account';
  calculateAccountInterestPreview();
}

async function submitAccount(e) {
  e.preventDefault();
  const accId = document.getElementById('account-id').value;
  const payload = {
    name: document.getElementById('account-name').value,
    institution: document.getElementById('account-institution').value,
    account_type: document.getElementById('account-type').value,
    balance: parseFloat(document.getElementById('account-balance').value || 0),
    interest_rate_pa: parseFloat(document.getElementById('account-rate-pa').value || 0),
    notes: document.getElementById('account-notes').value
  };
  try {
    let res;
    if (accId) {
      res = await fetch(`/api/accounts/${accId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    } else {
      res = await fetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    }
    if (res.ok) {
      closeModal('modal-account');
      triggerBouncyCelebration();
      showToast('Bank Account logged! 🏦');
      loadAccounts();
      loadSummary();
    }
  } catch (err) {
    showToast('Failed to save account', 'error');
  }
}

async function deleteAccount(id) {
  if (!confirm('Are you sure you want to remove this bank account?')) return;
  await fetch(`/api/accounts/${id}`, { method: 'DELETE', credentials: 'include' });
  showToast('Account removed');
  loadAccounts();
  loadSummary();
}

function openQuickBalanceModal(id, currentBalance, name) {
  document.getElementById('quick-acc-id').value = id;
  document.getElementById('quick-acc-balance').value = currentBalance;
  document.getElementById('quick-acc-label').innerText = `Update Balance for ${name} (₱)`;
  openModal('modal-quick-balance');
}

async function submitQuickBalance(e) {
  e.preventDefault();
  const id = document.getElementById('quick-acc-id').value;
  const newBal = parseFloat(document.getElementById('quick-acc-balance').value || 0);
  const acc = activeAccountsCache.find(a => a.id == id);
  if (!acc) return;
  acc.balance = newBal;
  try {
    const res = await fetch(`/api/accounts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(acc),
      credentials: 'include'
    });
    if (res.ok) {
      closeModal('modal-quick-balance');
      triggerBouncyCelebration();
      showToast('Balance updated! 🚀');
      loadAccounts();
      loadSummary();
    }
  } catch (err) {
    showToast('Failed to update balance', 'error');
  }
}

async function loadAnalytics() {
  try {
    const res = await fetch('/api/summary', { credentials: 'include' });
    const data = await res.json();
    const txRes = await fetch('/api/transactions', { credentials: 'include' });
    const txData = await txRes.json();
    const txs = txData.transactions || [];
    const expenseTxs = txs.filter(t => t.type === 'expense');
    const uniqueDays = new Set(expenseTxs.map(t => t.date)).size || 1;
    const dailyAvg = (data.total_expense / uniqueDays) || 0;
    document.getElementById('analytics-daily-burn').innerText = `₱${dailyAvg.toFixed(2)} / day`;
    const recurringTotal = txs.filter(t => t.is_recurring && t.type === 'expense').reduce((a, b) => a + b.amount, 0);
    document.getElementById('analytics-recurring-total').innerText = `₱${recurringTotal.toFixed(2)} / mo`;
    const fixedPct = data.total_expense > 0 ? Math.round((recurringTotal / data.total_expense) * 100) : 0;
    const discPct = Math.max(0, 100 - fixedPct);
    document.getElementById('analytics-ratio').innerText = `${fixedPct}% Fixed : ${discPct}% Flexible`;
    const catContainer = document.getElementById('analytics-category-bars');
    if (catContainer && data.category_breakdown) {
      catContainer.innerHTML = data.category_breakdown.map(c => {
        const pct = data.total_expense > 0 ? Math.round((c.total / data.total_expense) * 100) : 0;
        return `
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-xs font-semibold">
              <span class="text-slate-200">${escapeHtml(c.category)}</span>
              <span class="text-white font-bold">₱${c.total.toFixed(2)} (${pct}%)</span>
            </div>
            <div class="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-brand-500 to-pink-500 h-full rounded-full" style="width: ${pct}%"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Error loading analytics:', err);
  }
}

function renderCashflowChart(trends) {
  const ctx = document.getElementById('cashflow-chart')?.getContext('2d');
  if (!ctx) return;
  if (cashflowChartInstance) cashflowChartInstance.destroy();
  const labels = trends.length > 0 ? trends.map(t => t.month) : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const incomeData = trends.length > 0 ? trends.map(t => t.income) : [0, 0, 0, 0, 0, 0];
  const expenseData = trends.length > 0 ? trends.map(t => t.expense) : [0, 0, 0, 0, 0, 0];
  cashflowChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Income',
          data: incomeData,
          backgroundColor: '#10b981',
          borderRadius: 8,
        },
        {
          label: 'Expenses',
          data: expenseData,
          backgroundColor: '#f43f5e',
          borderRadius: 8,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          padding: 10,
          cornerRadius: 10,
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || '';
              if (label) label += ': ';
              if (context.parsed.y !== null) {
                label += '₱' + context.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2 });
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { size: 11 } }
        },
        y: {
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          ticks: {
            color: '#94a3b8',
            font: { size: 11 },
            callback: v => `₱${v}`
          }
        }
      }
    }
  });
}

function renderCategoryChart(breakdown) {
  const ctx = document.getElementById('category-chart')?.getContext('2d');
  if (!ctx) return;
  if (categoryChartInstance) categoryChartInstance.destroy();
  const labels = breakdown.length > 0 ? breakdown.map(b => b.category) : ['No Data'];
  const data = breakdown.length > 0 ? breakdown.map(b => b.total) : [1];
  const colors = [
    '#6366f1', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#8b5cf6', '#f43f5e', '#64748b'
  ];
  categoryChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 0,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, padding: 12, color: '#94a3b8', font: { size: 11 } }
        }
      }
    }
  });
}

function setTxType(type) {
  document.getElementById('tx-type').value = type;
  const expBtn = document.getElementById('tx-type-expense-btn');
  const incBtn = document.getElementById('tx-type-income-btn');
  const iconBg = document.getElementById('tx-modal-icon-bg');
  if (type === 'expense') {
    expBtn.className = 'py-2 rounded-xl text-xs font-bold transition-all bg-rose-500 text-white shadow-md anim-rubber';
    incBtn.className = 'py-2 rounded-xl text-xs font-bold transition-all text-slate-400 hover:text-white';
    iconBg.className = 'w-10 h-10 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center';
  } else {
    incBtn.className = 'py-2 rounded-xl text-xs font-bold transition-all bg-emerald-500 text-white shadow-md anim-rubber';
    expBtn.className = 'py-2 rounded-xl text-xs font-bold transition-all text-slate-400 hover:text-white';
    iconBg.className = 'w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center';
  }
}

async function submitTransaction(e) {
  e.preventDefault();
  const txId = document.getElementById('tx-id').value;
  const payload = {
    type: document.getElementById('tx-type').value,
    amount: parseFloat(document.getElementById('tx-amount').value),
    date: document.getElementById('tx-date').value,
    description: document.getElementById('tx-description').value,
    category: document.getElementById('tx-category').value,
    payment_method: document.getElementById('tx-payment-method').value,
    deal_id: document.getElementById('tx-deal-id').value || null,
    is_recurring: document.getElementById('tx-is-recurring').checked ? 1 : 0
  };
  try {
    let res;
    if (txId) {
      res = await fetch(`/api/transactions/${txId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    } else {
      res = await fetch('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    }
    if (res.ok) {
      closeModal('modal-transaction');
      triggerBouncyCelebration();
      showToast('Transaction logged successfully! 🚀');
      loadAllData();
    }
  } catch (err) {
    showToast('Failed to save transaction', 'error');
  }
}

function calculateDealSavings() {
  const orig = parseFloat(document.getElementById('deal-original-price').value) || 0;
  const deal = parseFloat(document.getElementById('deal-deal-price').value) || 0;
  const saved = Math.max(0, orig - deal);
  const pct = orig > 0 ? Math.round((saved / orig) * 100) : 0;
  document.getElementById('deal-savings-preview').innerText = `₱${saved.toFixed(2)} (${pct}% OFF)`;
}

async function submitDeal(e) {
  e.preventDefault();
  const dealId = document.getElementById('deal-id').value;
  const orig = parseFloat(document.getElementById('deal-original-price').value) || 0;
  const deal = parseFloat(document.getElementById('deal-deal-price').value) || 0;
  const payload = {
    title: document.getElementById('deal-title').value,
    original_price: orig,
    deal_price: deal,
    amount_saved: Math.max(0, orig - deal),
    store: document.getElementById('deal-store').value,
    status: document.getElementById('deal-status').value,
    url_or_notes: document.getElementById('deal-notes').value
  };
  try {
    let res;
    if (dealId) {
      res = await fetch(`/api/deals/${dealId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    } else {
      res = await fetch('/api/deals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    }
    if (res.ok) {
      closeModal('modal-deal');
      triggerBouncyCelebration();
      showToast('Bargain & Deal tracked! 🎉');
      loadDeals();
      loadSummary();
    }
  } catch (err) {
    showToast('Failed to save deal', 'error');
  }
}

async function submitBudget(e) {
  e.preventDefault();
  const payload = {
    category: document.getElementById('budget-category').value,
    monthly_limit: parseFloat(document.getElementById('budget-limit').value)
  };
  try {
    const res = await fetch('/api/budgets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include'
    });
    if (res.ok) {
      closeModal('modal-budget');
      showToast('Budget saved!');
      loadBudgets();
      loadSummary();
    }
  } catch (err) {
    showToast('Failed to save budget', 'error');
  }
}

async function submitGoal(e) {
  e.preventDefault();
  const goalId = document.getElementById('goal-id').value;
  const payload = {
    title: document.getElementById('goal-title').value,
    target_amount: parseFloat(document.getElementById('goal-target').value),
    current_amount: parseFloat(document.getElementById('goal-current').value || 0),
    target_date: document.getElementById('goal-date').value
  };
  try {
    let res;
    if (goalId) {
      res = await fetch(`/api/goals/${goalId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    } else {
      res = await fetch('/api/goals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });
    }
    if (res.ok) {
      closeModal('modal-goal');
      triggerBouncyCelebration();
      showToast('Savings Goal updated! 🎯');
      loadGoals();
    }
  } catch (err) {
    showToast('Failed to save goal', 'error');
  }
}

async function deleteTransaction(id) {
  if (!confirm('Are you sure you want to delete this transaction?')) return;
  await fetch(`/api/transactions/${id}`, { method: 'DELETE', credentials: 'include' });
  showToast('Transaction removed');
  loadAllData();
}

async function deleteDeal(id) {
  if (!confirm('Remove this deal?')) return;
  await fetch(`/api/deals/${id}`, { method: 'DELETE', credentials: 'include' });
  showToast('Deal removed');
  loadDeals();
  loadSummary();
}

async function deleteBudget(id) {
  if (!confirm('Delete budget limit?')) return;
  await fetch(`/api/budgets/${id}`, { method: 'DELETE', credentials: 'include' });
  showToast('Budget deleted');
  loadBudgets();
  loadSummary();
}

async function deleteGoal(id) {
  if (!confirm('Remove this savings goal?')) return;
  await fetch(`/api/goals/${id}`, { method: 'DELETE', credentials: 'include' });
  showToast('Goal removed');
  loadGoals();
}

async function claimDealAsExpense(dealId) {
  const deal = activeDealsCache.find(d => d.id === dealId);
  if (!deal) return;
  openTransactionModal();
  setTxType('expense');
  document.getElementById('tx-amount').value = deal.deal_price;
  document.getElementById('tx-description').value = `${deal.title} (Saved ₱${deal.amount_saved.toFixed(2)})`;
  document.getElementById('tx-category').value = deal.category || 'Shopping & Deals';
  document.getElementById('tx-deal-id').value = deal.id;
}

async function contributeToGoal(id, current) {
  const add = prompt('How much money would you like to deposit towards this goal? (₱)', '500');
  if (!add || isNaN(parseFloat(add))) return;
  const newAmount = current + parseFloat(add);
  const goal = (await (await fetch('/api/goals', { credentials: 'include' })).json()).goals.find(g => g.id === id);
  if (!goal) return;
  goal.current_amount = newAmount;
  await fetch(`/api/goals/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(goal),
    credentials: 'include'
  });
  triggerBouncyCelebration();
  showToast(`Deposited ₱${parseFloat(add).toFixed(2)} to ${goal.title}! 🎉`);
  loadGoals();
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('hidden');
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('hidden');
}

function openTransactionModal() {
  document.getElementById('tx-form').reset();
  document.getElementById('tx-id').value = '';
  document.getElementById('tx-modal-title').innerText = 'Log Transaction';
  setDefaultDates();
  setTxType('expense');
  openModal('modal-transaction');
}

function openQuickExpenseModal() {
  openTransactionModal();
  setTxType('expense');
}

function openQuickIncomeModal() {
  openTransactionModal();
  setTxType('income');
}

function openDealModal() {
  document.getElementById('deal-form').reset();
  document.getElementById('deal-id').value = '';
  document.getElementById('deal-modal-title').innerText = 'Log Deal or Bargain';
  calculateDealSavings();
  openModal('modal-deal');
}

function openBudgetModal() {
  document.getElementById('budget-form').reset();
  openModal('modal-budget');
}

function openGoalModal() {
  document.getElementById('goal-form').reset();
  document.getElementById('goal-id').value = '';
  openModal('modal-goal');
}

function openAddMoneyModal() {
  document.getElementById('add-money-form').reset();
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('add-money-date').value = today;
  openModal('modal-add-money');
}

async function submitAddMoney(e) {
  e.preventDefault();
  const amount = parseFloat(document.getElementById('add-money-amount').value);
  const date = document.getElementById('add-money-date').value;
  const note = document.getElementById('add-money-note').value || 'Added money';
  const payload = {
    type: 'income',
    amount: amount,
    date: date,
    description: note,
    category: 'Deposit',
    payment_method: 'Cash',
    deal_id: null,
    is_recurring: 0
  };
  try {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include'
    });
    if (res.ok) {
      closeModal('modal-add-money');
      triggerBouncyCelebration();
      showToast(`Added ₱${amount.toFixed(2)} to your vault! 🎉`);
      loadAllData();
    } else {
      showToast('Failed to add money', 'error');
    }
  } catch (err) {
    showToast('Error adding money', 'error');
  }
}

function editTransaction(tx) {
  openTransactionModal();
  document.getElementById('tx-id').value = tx.id;
  document.getElementById('tx-amount').value = tx.amount;
  document.getElementById('tx-date').value = tx.date;
  document.getElementById('tx-description').value = tx.description;
  document.getElementById('tx-category').value = tx.category;
  document.getElementById('tx-payment-method').value = tx.payment_method || 'Cash';
  document.getElementById('tx-is-recurring').checked = !!tx.is_recurring;
  document.getElementById('tx-deal-id').value = tx.deal_id || '';
  document.getElementById('tx-modal-title').innerText = 'Edit Transaction';
  setTxType(tx.type);
}

function editDeal(deal) {
  openDealModal();
  document.getElementById('deal-id').value = deal.id;
  document.getElementById('deal-title').value = deal.title;
  document.getElementById('deal-original-price').value = deal.original_price;
  document.getElementById('deal-deal-price').value = deal.deal_price;
  document.getElementById('deal-store').value = deal.store || '';
  document.getElementById('deal-status').value = deal.status || 'active';
  document.getElementById('deal-notes').value = deal.url_or_notes || '';
  document.getElementById('deal-modal-title').innerText = 'Edit Deal';
  calculateDealSavings();
}

function toggleMenu(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('hidden');
}

document.addEventListener('click', (e) => {
  const menu = document.getElementById('settings-menu');
  if (menu && !menu.contains(e.target) && !e.target.closest('button[onclick*="settings-menu"]')) {
    menu.classList.add('hidden');
  }
});

async function seedDemoData() {
  try {
    const res = await fetch('/api/seed', { method: 'POST', credentials: 'include' });
    if (res.ok) {
      triggerBouncyCelebration();
      showToast('Loaded demo dataset! 🚀');
      loadAllData();
    }
  } catch (err) {
    showToast('Failed to seed demo data', 'error');
  }
}

function exportDataCSV() {
  window.location.href = '/api/export/csv';
  showToast('CSV export downloaded!');
}

async function exportDataJSON() {
  const res = await fetch('/api/export/json', { credentials: 'include' });
  const data = await res.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `bouncy_finance_backup_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  showToast('Full JSON backup downloaded!');
}

function triggerFileInput() {
  document.getElementById('json-file-input').click();
}

async function importDataJSON(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (event) => {
    try {
      const data = JSON.parse(event.target.result);
      const res = await fetch('/api/import/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        credentials: 'include'
      });
      if (res.ok) {
        triggerBouncyCelebration();
        showToast('Backup restored successfully!');
        loadAllData();
      }
    } catch (err) {
      showToast('Invalid backup JSON file', 'error');
    }
  };
  reader.readAsText(file);
}

async function resetAllData() {
  if (!confirm('WARNING: This will permanently delete all logged transactions, deals, and budgets! Continue?')) return;
  await fetch('/api/reset', { method: 'POST', credentials: 'include' });
  showToast('All data cleared');
  loadAllData();
}

function triggerBouncyCelebration() {
  if (typeof confetti === 'function') {
    confetti({
      particleCount: 70,
      spread: 60,
      origin: { y: 0.8 },
      colors: ['#6366f1', '#ec4899', '#10b981', '#f59e0b']
    });
  }
}

function showToast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  const bgColor = type === 'success' ? 'bg-brand-600 text-white' : 'bg-rose-600 text-white';
  const icon = type === 'success' ? 'ph-check-circle' : 'ph-warning-circle';
  toast.className = `flex items-center gap-2.5 px-4 py-3 rounded-2xl ${bgColor} shadow-2xl text-sm font-semibold anim-modal-pop`;
  toast.innerHTML = `<i class="ph ${icon} text-lg"></i> <span>${escapeHtml(msg)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
