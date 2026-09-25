/**
 * utils.js — Shared utility functions used across all pages
 */

// ── Auth Guard ───────────────────────────────────────────
// Call this at the top of any protected page to redirect if not logged in
function requireAuth() {
    const token = localStorage.getItem('sw_token');
    if (!token) { window.location.href = 'index.html'; return false; }
    return true;
}

function requireGuest() {
    const token = localStorage.getItem('sw_token');
    if (token) { window.location.href = 'dashboard.html'; return false; }
    return true;
}

// ── Toast Notifications ───────────────────────────────────
function toast(message, type = 'info') {
    const icons = { success: '✓', error: '✕', info: '●' };
    const container = document.getElementById('toast-container') || createToastContainer();
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
    container.appendChild(el);
    setTimeout(() => el.remove(), 3200);
}

function createToastContainer() {
    const el = document.createElement('div');
    el.id = 'toast-container';
    document.body.appendChild(el);
    return el;
}

// ── Modal Helpers ─────────────────────────────────────────
function openModal(id) {
    document.getElementById(id).classList.add('open');
    document.body.style.overflow = 'hidden';
}
function closeModal(id) {
    document.getElementById(id).classList.remove('open');
    document.body.style.overflow = '';
}

// Close modals when clicking overlay background
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
        document.body.style.overflow = '';
    }
});

// ── Tab System ────────────────────────────────────────────
function initTabs(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const buttons = container.querySelectorAll('.tab-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-panel').forEach(p => {
                p.classList.toggle('active', p.id === target);
            });
        });
    });
}

// ── Loading State ─────────────────────────────────────────
function setLoading(btnEl, loading) {
    if (loading) {
        btnEl.disabled = true;
        btnEl.dataset.originalText = btnEl.innerHTML;
        btnEl.classList.add('btn-loading');
        btnEl.innerHTML = '';
    } else {
        btnEl.disabled = false;
        btnEl.classList.remove('btn-loading');
        btnEl.innerHTML = btnEl.dataset.originalText || '';
    }
}

// ── Formatting ────────────────────────────────────────────
function formatCurrency(amount) {
    const num = parseFloat(amount);
    return '₹' + Math.abs(num).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getInitials(name) {
    return (name || '?').split(' ').slice(0,2).map(w => w[0]).join('').toUpperCase();
}

function splitTypeEmoji(type) {
    return { equal: '⚖️', exact: '💎', percentage: '%️' }[type] || '💸';
}

function expenseEmoji(desc = '') {
    const d = desc.toLowerCase();
    if (d.includes('food') || d.includes('dinner') || d.includes('lunch') || d.includes('breakfast') || d.includes('restaurant')) return '🍽️';
    if (d.includes('hotel') || d.includes('stay') || d.includes('rent') || d.includes('room')) return '🏨';
    if (d.includes('cab') || d.includes('taxi') || d.includes('uber') || d.includes('ola') || d.includes('transport')) return '🚗';
    if (d.includes('movie') || d.includes('show') || d.includes('ticket')) return '🎬';
    if (d.includes('grocery') || d.includes('shop') || d.includes('mart')) return '🛒';
    if (d.includes('fuel') || d.includes('petrol') || d.includes('gas')) return '⛽';
    if (d.includes('party') || d.includes('bar') || d.includes('drink')) return '🎉';
    if (d.includes('flight') || d.includes('air') || d.includes('airport')) return '✈️';
    return '💸';
}

// ── User Session ─────────────────────────────────────────
function saveSession(token, user) {
    localStorage.setItem('sw_token', token);
    localStorage.setItem('sw_user', JSON.stringify(user));
    // Clear legacy sessionStorage if any exists
    sessionStorage.removeItem('sw_token');
    sessionStorage.removeItem('sw_user');
}

function getUser() {
    try {
        const userStr = localStorage.getItem('sw_user') || sessionStorage.getItem('sw_user');
        return userStr ? JSON.parse(userStr) : null;
    } catch {
        return null;
    }
}

function logout() {
    localStorage.removeItem('sw_token');
    localStorage.removeItem('sw_user');
    sessionStorage.removeItem('sw_token');
    sessionStorage.removeItem('sw_user');
    window.location.href = 'index.html';
}

// ── Animated Orbs Background ─────────────────────────────
function initBackground() {
    const canvas = document.querySelector('.bg-canvas');
    if (canvas) return; // Already exists
    const div = document.createElement('div');
    div.className = 'bg-canvas';
    div.innerHTML = `
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>`;
    document.body.prepend(div);
}

// ── Theme (Light / Dark) ─────────────────────────────────
// Reads saved preference from localStorage, falls back to OS preference
function initTheme() {
    const saved = localStorage.getItem('sw_theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('sw_theme', next);
}

// Apply theme immediately on script load to prevent flash of wrong theme
initTheme();

// ── Avatar URL Helper ─────────────────────────────────────
function getAvatarUrl(profilePicture) {
    if (!profilePicture) return null;
    return `/uploads/avatars/${profilePicture}`;
}

// ── Render Navbar ─────────────────────────────────────────
function renderNavbar(activeBack = null) {
    const user = getUser();
    const initials = getInitials(user?.name);
    const avatarUrl = getAvatarUrl(user?.profile_picture);
    const avatarContent = avatarUrl
        ? `<img src="${avatarUrl}" alt="${escapeHtml(user?.name)}" style="width:100%;height:100%;object-fit:cover;border-radius:50%">`
        : initials;
    const backBtn = activeBack
        ? `<button class="btn btn-ghost btn-sm" onclick="history.back()">← ${activeBack}</button>`
        : '';
    return `
    <nav class="navbar">
      <div style="display:flex;align-items:center;gap:16px">
        <a href="dashboard.html" class="navbar-brand">
          <span class="logo-icon"><img src="logo.jpg" alt="SettleUp" style="width:100%;height:100%;object-fit:cover;border-radius:inherit"></span>
          <span class="gradient-text">SettleUp</span>
        </a>
        ${backBtn}
      </div>
      <div class="navbar-right">
        <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"/>
            <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
            <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
          </svg>
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        </button>
        <a href="profile.html" class="user-chip" title="Edit Profile">
          <div class="user-avatar">${avatarContent}</div>
          <span class="user-name">${user?.name || 'User'}</span>
        </a>
        <button class="btn btn-ghost btn-sm" onclick="logout()">Logout</button>
      </div>
    </nav>`;
}

// ── Escape HTML ──────────────────────────────────────────
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ── Skeleton Card ────────────────────────────────────────
function skeletonCard(height = '100px') {
    return '<div class="skeleton" style="height:' + height + '"></div>';
}

// Attach to global scope
window.requireAuth = requireAuth;
window.requireGuest = requireGuest;
window.toast = toast;
window.openModal = openModal;
window.closeModal = closeModal;
window.initTabs = initTabs;
window.setLoading = setLoading;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.getInitials = getInitials;
window.splitTypeEmoji = splitTypeEmoji;
window.expenseEmoji = expenseEmoji;
window.saveSession = saveSession;
window.getUser = getUser;
window.logout = logout;
window.initBackground = initBackground;
window.initTheme = initTheme;
window.toggleTheme = toggleTheme;
window.getAvatarUrl = getAvatarUrl;
window.renderNavbar = renderNavbar;
window.skeletonCard = skeletonCard;
window.escapeHtml = escapeHtml;
