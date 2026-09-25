/**
 * api.js — All backend API calls in one place
 *
 * WHY centralize this?
 * Every component/page needs to call the backend. If we write fetch()
 * calls inline everywhere, we'd repeat error handling everywhere.
 * Instead, every call goes through apiCall() which handles:
 *   - Auth header injection
 *   - JSON parsing
 *   - Consistent error throwing
 */

const API_BASE = window.location.origin;

function getToken() {
    return localStorage.getItem('sw_token');
}

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

async function apiCall(method, endpoint, body = null) {
    const options = { method, headers: getAuthHeaders() };
    if (body) options.body = JSON.stringify(body);

    // Cache-bust GET requests to always get fresh data
    let url = `${API_BASE}${endpoint}`;
    if (method === 'GET') {
        const sep = url.includes('?') ? '&' : '?';
        url += `${sep}_t=${Date.now()}`;
    }

    let response;
    try {
        response = await fetch(url, options);
    } catch (err) {
        // Network error — server likely not running
        throw { code: 'NETWORK_ERROR', error: 'Cannot reach the server. Is the Flask API running?' };
    }

    const data = await response.json();

    if (!response.ok) {
        // Token expired / invalid user / unauthorized → clear session and redirect to login
        if (response.status === 401 && !endpoint.startsWith('/api/auth/login') && !endpoint.startsWith('/api/auth/register')) {
            localStorage.removeItem('sw_token');
            localStorage.removeItem('sw_user');
            sessionStorage.removeItem('sw_token');
            sessionStorage.removeItem('sw_user');
            const path = window.location.pathname;
            if (!path.endsWith('index.html') && path !== '/' && !path.endsWith('/')) {
                window.location.href = 'index.html';
            }
        }
        throw data; // Let the caller handle it (contains { error, code })
    }
    return data;
}

// ── Auth ─────────────────────────────────────────────────
const Auth = {
    register: (name, email, password) =>
        apiCall('POST', '/api/auth/register', { name, email, password }),

    login: (email, password) =>
        apiCall('POST', '/api/auth/login', { email, password }),

    me: () => apiCall('GET', '/api/auth/me'),
};

// ── Groups ───────────────────────────────────────────────
const Groups = {
    create: (name) =>
        apiCall('POST', '/api/groups', { name }),

    list: () => apiCall('GET', '/api/groups'),

    addMember: (groupId, email, name = '', autoCreate = true) =>
        apiCall('POST', `/api/groups/${groupId}/members`, { email, name, auto_create: autoCreate }),

    getMembers: (groupId) =>
        apiCall('GET', `/api/groups/${groupId}/members`),

    listUsers: () =>
        apiCall('GET', '/api/groups/users'),
};

// ── Expenses ─────────────────────────────────────────────
const Expenses = {
    add: (groupId, data) =>
        apiCall('POST', `/api/groups/${groupId}/expenses`, data),

    list: (groupId) =>
        apiCall('GET', `/api/groups/${groupId}/expenses`),
};

// ── Balances ─────────────────────────────────────────────
const Balances = {
    get: (groupId) =>
        apiCall('GET', `/api/groups/${groupId}/balances`),

    simplified: (groupId) =>
        apiCall('GET', `/api/groups/${groupId}/simplified-debts`),
};

// ── Settlements ──────────────────────────────────────────
const Settlements = {
    record: (groupId, paidTo, amount, note, paidBy = null) => {
        const payload = { paid_to: paidTo, amount, note };
        if (paidBy !== null && paidBy !== undefined) payload.paid_by = paidBy;
        return apiCall('POST', `/api/groups/${groupId}/settlements`, payload);
    },

    list: (groupId) =>
        apiCall('GET', `/api/groups/${groupId}/settlements`),
};

// ── File Upload Helper ───────────────────────────────────
async function apiUpload(endpoint, file, fieldName = 'file') {
    const formData = new FormData();
    formData.append(fieldName, file);

    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    let response;
    try {
        response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers,
            body: formData,
        });
    } catch (err) {
        throw { code: 'NETWORK_ERROR', error: 'Cannot reach the server.' };
    }

    const data = await response.json();
    if (!response.ok) throw data;
    return data;
}

// ── Profile ──────────────────────────────────────────────
const Profile = {
    get: () => apiCall('GET', '/api/profile'),

    update: (name) =>
        apiCall('PUT', '/api/profile', { name }),

    uploadPicture: (file) =>
        apiUpload('/api/profile/picture', file),

    deletePicture: () =>
        apiCall('DELETE', '/api/profile/picture'),
};

// Export to global scope (no build step needed)
window.API = { Auth, Groups, Expenses, Balances, Settlements, Profile };
