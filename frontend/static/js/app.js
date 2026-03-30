/* ============================================================
   PO Management System — Frontend Application (Vanilla JS)
   ============================================================ */

'use strict';

// ── State ─────────────────────────────────────────────────────
const STATE = {
  token: null,
  user:  null,
  vendors:  [],
  products: [],
  lineItems: [],   // [{id, productId, qty, unitPrice}]
  nextRowId: 0,
};

// ── API helpers ───────────────────────────────────────────────
const API_BASE = '/api';

async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (STATE.token) headers['Authorization'] = `Bearer ${STATE.token}`;
  const res = await fetch(`${API_BASE}${path}`, { headers, ...options });
  if (res.status === 401) { doLogout(); return null; }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  get:    (p)    => apiFetch(p),
  post:   (p, d) => apiFetch(p, { method: 'POST',  body: JSON.stringify(d) }),
  put:    (p, d) => apiFetch(p, { method: 'PUT',   body: JSON.stringify(d) }),
  patch:  (p, d) => apiFetch(p, { method: 'PATCH', body: JSON.stringify(d) }),
  delete: (p)    => apiFetch(p, { method: 'DELETE' }),
};

// ── Toast ─────────────────────────────────────────────────────
let _toastTimer = null;
function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast${type === 'error' ? ' error' : ''}`;
  el.classList.remove('hidden');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.add('hidden'), 3200);
}

// ── Navigation ────────────────────────────────────────────────
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');

  const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navEl) navEl.classList.add('active');

  // Load data for each page
  if (page === 'dashboard')   loadDashboard();
  if (page === 'orders')      loadOrders();
  if (page === 'create-po')   initCreatePO();
  if (page === 'vendors')     loadVendors();
  if (page === 'products')    loadProducts();
}

// ── Auth ──────────────────────────────────────────────────────
function saveSession(token, user) {
  STATE.token = token;
  STATE.user  = user;
  try { sessionStorage.setItem('po_token', token); sessionStorage.setItem('po_user', JSON.stringify(user)); } catch(_) {}
}

function loadSession() {
  try {
    const t = sessionStorage.getItem('po_token');
    const u = sessionStorage.getItem('po_user');
    if (t && u) { STATE.token = t; STATE.user = JSON.parse(u); return true; }
  } catch(_) {}
  return false;
}

function doLogout() {
  STATE.token = null; STATE.user = null;
  try { sessionStorage.clear(); } catch(_) {}
  document.getElementById('app').classList.add('hidden');
  document.getElementById('login-screen').classList.remove('hidden');
}

function showApp() {
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  const name = STATE.user?.name || STATE.user?.email || 'User';
  document.getElementById('user-name').textContent = name;
  document.getElementById('user-role').textContent = STATE.user?.role || 'user';
  document.getElementById('user-initials').textContent =
    name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  navigate('dashboard');
}

// ── Login ─────────────────────────────────────────────────────
document.getElementById('login-btn').addEventListener('click', async () => {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value.trim();
  const errEl    = document.getElementById('login-error');
  errEl.classList.add('hidden');

  if (!username || !password) {
    errEl.textContent = 'Please enter username and password.';
    errEl.classList.remove('hidden');
    return;
  }

  const btn = document.getElementById('login-btn');
  btn.textContent = 'SIGNING IN…';
  btn.disabled = true;

  try {
    const res = await fetch('/auth/demo-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || 'Invalid credentials');
    }
    const data = await res.json();
    saveSession(data.access_token, data.user);
    showApp();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.textContent = 'SIGN IN →';
    btn.disabled = false;
  }
});

// Enter key on password
document.getElementById('login-pass').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('login-btn').click();
});

// Login tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
  });
});

document.getElementById('logout-btn').addEventListener('click', doLogout);

// ── Sidebar nav ───────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    navigate(item.dataset.page);
  });
});

// ── Utilities ─────────────────────────────────────────────────
const fmt = n => '₹ ' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function statusBadge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

function stars(rating) {
  const n = Math.round(parseFloat(rating) || 0);
  return '<span class="rating">' + '★'.repeat(n) + '☆'.repeat(5 - n) + `</span> <span style="color:var(--text-muted);font-size:0.75rem">${rating}</span>`;
}

// ── Dashboard ─────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const orders = await api.get('/purchase-orders?limit=50');
    if (!orders) return;

    const total    = orders.length;
    const pending  = orders.filter(o => o.status === 'PENDING').length;
    const approved = orders.filter(o => o.status === 'APPROVED').length;
    const value    = orders.reduce((s, o) => s + parseFloat(o.total_amount || 0), 0);

    document.getElementById('stat-total').textContent   = total;
    document.getElementById('stat-pending').textContent = pending;
    document.getElementById('stat-approved').textContent = approved;
    document.getElementById('stat-value').textContent   = fmt(value);

    const tbody = document.getElementById('dashboard-tbody');
    if (!orders.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading-row">No purchase orders yet.</td></tr>';
      return;
    }
    tbody.innerHTML = orders.slice(0, 10).map(o => `
      <tr>
        <td style="font-family:var(--mono);font-size:0.75rem;color:var(--accent)">${o.reference_no}</td>
        <td>${o.vendor_name || '—'}</td>
        <td style="font-family:var(--mono)">${fmt(o.total_amount)}</td>
        <td>${statusBadge(o.status)}</td>
        <td style="color:var(--text-muted);font-size:0.75rem">${fmtDate(o.created_at)}</td>
        <td><button class="btn-outline btn-sm" onclick="viewPO(${o.id})">VIEW</button></td>
      </tr>`).join('');
  } catch (e) {
    toast(e.message, 'error');
  }
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ── Orders ────────────────────────────────────────────────────
async function loadOrders() {
  const statusFilter = document.getElementById('filter-status').value;
  const qs = statusFilter ? `?status_filter=${statusFilter}` : '';
  try {
    const orders = await api.get(`/purchase-orders${qs}`);
    if (!orders) return;
    const tbody = document.getElementById('orders-tbody');
    if (!orders.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="loading-row">No orders found.</td></tr>';
      return;
    }
    tbody.innerHTML = orders.map(o => `
      <tr>
        <td style="font-family:var(--mono);font-size:0.75rem;color:var(--accent)">${o.reference_no}</td>
        <td>${o.vendor_name || '—'}</td>
        <td style="font-family:var(--mono)">${fmt(parseFloat(o.total_amount) / 1.05)}</td>
        <td style="font-family:var(--mono);color:var(--text-muted)">${fmt(parseFloat(o.total_amount) - parseFloat(o.total_amount) / 1.05)}</td>
        <td style="font-family:var(--mono);font-weight:700">${fmt(o.total_amount)}</td>
        <td>${statusBadge(o.status)}</td>
        <td style="color:var(--text-muted);font-size:0.75rem">${fmtDate(o.created_at)}</td>
        <td>
          <button class="btn-outline btn-sm" onclick="viewPO(${o.id})">VIEW</button>
        </td>
      </tr>`).join('');
  } catch (e) {
    toast(e.message, 'error');
  }
}

document.getElementById('filter-status').addEventListener('change', loadOrders);

// ── PO Detail Modal ───────────────────────────────────────────
async function viewPO(id) {
  try {
    const po = await api.get(`/purchase-orders/${id}`);
    if (!po) return;

    document.getElementById('po-detail-ref').textContent = po.reference_no;

    const body = document.getElementById('po-detail-body');
    body.innerHTML = `
      <dl class="po-meta">
        <div><dt>VENDOR</dt><dd>${po.vendor?.name || po.vendor_id}</dd></div>
        <div><dt>STATUS</dt><dd>${statusBadge(po.status)}</dd></div>
        <div><dt>CREATED BY</dt><dd>${po.created_by || '—'}</dd></div>
        <div><dt>DATE</dt><dd>${fmtDate(po.created_at)}</dd></div>
        ${po.notes ? `<div style="grid-column:1/-1"><dt>NOTES</dt><dd>${po.notes}</dd></div>` : ''}
      </dl>
      <table class="data-table" style="margin-bottom:1rem">
        <thead><tr><th>PRODUCT</th><th>SKU</th><th>QTY</th><th>UNIT PRICE</th><th>LINE TOTAL</th></tr></thead>
        <tbody>
          ${po.line_items.map(li => `
            <tr>
              <td>${li.product?.name || li.product_id}</td>
              <td style="font-family:var(--mono);font-size:0.7rem;color:var(--text-muted)">${li.product?.sku || ''}</td>
              <td>${li.quantity}</td>
              <td style="font-family:var(--mono)">${fmt(li.unit_price)}</td>
              <td style="font-family:var(--mono);font-weight:700">${fmt(li.line_total)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
      <div style="text-align:right;font-family:var(--mono);line-height:2">
        <div style="color:var(--text-muted)">Subtotal: ${fmt(po.subtotal)}</div>
        <div style="color:var(--text-muted)">Tax (5%): ${fmt(po.tax_amount)}</div>
        <div style="color:var(--accent);font-size:1rem;font-weight:700">TOTAL: ${fmt(po.total_amount)}</div>
      </div>`;

    // Status action buttons
    const transitions = {
      DRAFT:    ['PENDING', 'CANCELLED'],
      PENDING:  ['APPROVED', 'CANCELLED'],
      APPROVED: ['ORDERED', 'CANCELLED'],
      ORDERED:  ['RECEIVED'],
    };
    const actions = document.getElementById('po-detail-actions');
    const next = transitions[po.status] || [];
    actions.innerHTML = `
      <button class="btn-outline" onclick="closePOModal()">Close</button>
      ${next.map(s => `
        <button class="btn-${s === 'CANCELLED' ? 'outline' : 'primary'}"
          onclick="updateStatus(${po.id}, '${s}')">
          → ${s}
        </button>`).join('')}`;

    document.getElementById('po-detail-modal').classList.remove('hidden');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function updateStatus(id, newStatus) {
  try {
    await api.patch(`/purchase-orders/${id}/status`, { status: newStatus });
    closePOModal();
    toast(`Status updated to ${newStatus}`);
    // Reload current page data
    const activePage = document.querySelector('.page.active')?.id?.replace('page-', '');
    if (activePage) navigate(activePage);
  } catch (e) {
    toast(e.message, 'error');
  }
}

function closePOModal() {
  document.getElementById('po-detail-modal').classList.add('hidden');
}

// ── Create PO ─────────────────────────────────────────────────
async function initCreatePO() {
  STATE.lineItems = [];
  STATE.nextRowId = 0;
  document.getElementById('line-items-container').innerHTML = '';
  document.getElementById('no-items-msg').classList.remove('hidden');
  document.getElementById('po-notes').value = '';
  updateTotals();

  // Load vendors & products in parallel
  try {
    const [vendors, products] = await Promise.all([
      api.get('/vendors?active_only=true'),
      api.get('/products?active_only=true'),
    ]);
    STATE.vendors  = vendors  || [];
    STATE.products = products || [];

    const vendorSel = document.getElementById('po-vendor');
    vendorSel.innerHTML = '<option value="">— Select Vendor —</option>' +
      STATE.vendors.map(v => `<option value="${v.id}">${v.name} (★${v.rating})</option>`).join('');
  } catch (e) {
    toast(e.message, 'error');
  }
}

document.getElementById('add-row-btn').addEventListener('click', addLineItemRow);

function addLineItemRow() {
  if (!STATE.products.length) { toast('No products loaded yet.', 'error'); return; }
  document.getElementById('no-items-msg').classList.add('hidden');

  const rowId = STATE.nextRowId++;
  STATE.lineItems.push({ rowId, productId: '', qty: 1, unitPrice: 0 });

  const productOptions = STATE.products.map(p =>
    `<option value="${p.id}" data-price="${p.unit_price}" data-cat="${p.category || ''}">${p.name} (${p.sku})</option>`
  ).join('');

  const row = document.createElement('div');
  row.className = 'line-item-row';
  row.id = `row-${rowId}`;
  row.innerHTML = `
    <select onchange="onProductChange(${rowId}, this)">
      <option value="">— Select Product —</option>
      ${productOptions}
    </select>
    <input type="number" min="1" value="1"
      onchange="onQtyChange(${rowId}, this)" oninput="onQtyChange(${rowId}, this)" />
    <input type="number" min="0" step="0.01" value="0"
      id="price-${rowId}"
      onchange="onPriceChange(${rowId}, this)" oninput="onPriceChange(${rowId}, this)" />
    <div class="line-total-cell" id="lt-${rowId}">₹ 0.00</div>
    <button class="btn-ai btn-sm" onclick="triggerAI(${rowId})" title="AI Auto-Description">✦ AI</button>
    <button class="btn-remove" onclick="removeRow(${rowId})" title="Remove">×</button>`;

  document.getElementById('line-items-container').appendChild(row);
}

function onProductChange(rowId, sel) {
  const item = STATE.lineItems.find(i => i.rowId === rowId);
  if (!item) return;
  item.productId = parseInt(sel.value) || '';
  const opt = sel.options[sel.selectedIndex];
  const price = parseFloat(opt.dataset.price) || 0;
  item.unitPrice = price;
  const priceInput = document.getElementById(`price-${rowId}`);
  if (priceInput) priceInput.value = price.toFixed(2);
  recalcRow(rowId);
}

function onQtyChange(rowId, input) {
  const item = STATE.lineItems.find(i => i.rowId === rowId);
  if (!item) return;
  item.qty = Math.max(1, parseInt(input.value) || 1);
  recalcRow(rowId);
}

function onPriceChange(rowId, input) {
  const item = STATE.lineItems.find(i => i.rowId === rowId);
  if (!item) return;
  item.unitPrice = parseFloat(input.value) || 0;
  recalcRow(rowId);
}

function recalcRow(rowId) {
  const item = STATE.lineItems.find(i => i.rowId === rowId);
  if (!item) return;
  const lt = item.qty * item.unitPrice;
  const el = document.getElementById(`lt-${rowId}`);
  if (el) el.textContent = fmt(lt);
  updateTotals();
}

function removeRow(rowId) {
  STATE.lineItems = STATE.lineItems.filter(i => i.rowId !== rowId);
  const row = document.getElementById(`row-${rowId}`);
  if (row) row.remove();
  if (!STATE.lineItems.length) document.getElementById('no-items-msg').classList.remove('hidden');
  updateTotals();
}

function updateTotals() {
  const subtotal = STATE.lineItems.reduce((s, i) => s + i.qty * i.unitPrice, 0);
  const tax      = subtotal * 0.05;
  const total    = subtotal + tax;
  document.getElementById('t-subtotal').textContent = fmt(subtotal);
  document.getElementById('t-tax').textContent      = fmt(tax);
  document.getElementById('t-total').textContent    = fmt(total);
}

// Submit PO
document.getElementById('submit-po-btn').addEventListener('click', async () => {
  const vendorId = parseInt(document.getElementById('po-vendor').value);
  if (!vendorId) { toast('Please select a vendor.', 'error'); return; }

  const validItems = STATE.lineItems.filter(i => i.productId && i.qty > 0 && i.unitPrice >= 0);
  if (!validItems.length) { toast('Add at least one product line item.', 'error'); return; }

  const payload = {
    vendor_id: vendorId,
    notes: document.getElementById('po-notes').value.trim() || null,
    line_items: validItems.map(i => ({
      product_id: i.productId,
      quantity:   i.qty,
      unit_price: i.unitPrice,
    })),
  };

  const btn = document.getElementById('submit-po-btn');
  btn.textContent = 'SUBMITTING…';
  btn.disabled = true;

  try {
    const po = await api.post('/purchase-orders', payload);
    if (po) {
      toast(`✓ PO ${po.reference_no} created — Total ${fmt(po.total_amount)}`);
      navigate('orders');
    }
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.textContent = 'SUBMIT ORDER →';
    btn.disabled = false;
  }
});

// ── AI Description ────────────────────────────────────────────
async function triggerAI(rowId) {
  const item = STATE.lineItems.find(i => i.rowId === rowId);
  if (!item || !item.productId) {
    toast('Select a product first.', 'error');
    return;
  }
  const product = STATE.products.find(p => p.id === item.productId);
  if (!product) return;

  document.getElementById('ai-product-name').textContent = `✦ ${product.name}`;
  document.getElementById('ai-result').textContent = 'Generating description…';
  document.getElementById('ai-modal').classList.remove('hidden');

  try {
    const res = await api.post('/ai/generate-description', {
      product_id:   product.id,
      product_name: product.name,
      category:     product.category || null,
    });
    if (res) {
      document.getElementById('ai-result').textContent = res.description;
      const modelEl = document.createElement('div');
      modelEl.style.cssText = 'font-family:var(--mono);font-size:0.6rem;color:var(--text-muted);margin-top:0.5rem;letter-spacing:0.08em';
      modelEl.textContent = `MODEL: ${res.model_used}`;
      document.getElementById('ai-result').appendChild(modelEl);
    }
  } catch (e) {
    document.getElementById('ai-result').textContent = 'Failed to generate description.';
  }
}

function closeAIModal() {
  document.getElementById('ai-modal').classList.add('hidden');
}

// ── Vendors ───────────────────────────────────────────────────
async function loadVendors() {
  try {
    const vendors = await api.get('/vendors?active_only=false');
    if (!vendors) return;
    const tbody = document.getElementById('vendors-tbody');
    if (!vendors.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading-row">No vendors found.</td></tr>';
      return;
    }
    tbody.innerHTML = vendors.map(v => `
      <tr>
        <td style="font-weight:500;color:var(--text-primary)">${v.name}</td>
        <td>${v.contact}</td>
        <td style="color:var(--text-muted)">${v.email || '—'}</td>
        <td style="color:var(--text-muted)">${v.phone || '—'}</td>
        <td>${stars(v.rating)}</td>
        <td>${v.is_active
          ? '<span style="color:var(--green);font-family:var(--mono);font-size:0.65rem">ACTIVE</span>'
          : '<span style="color:var(--red);font-family:var(--mono);font-size:0.65rem">INACTIVE</span>'}</td>
      </tr>`).join('');
  } catch (e) {
    toast(e.message, 'error');
  }
}

function openVendorModal() {
  ['v-name', 'v-contact', 'v-email', 'v-phone'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('v-rating').value = '3.0';
  document.getElementById('v-error').classList.add('hidden');
  document.getElementById('vendor-modal').classList.remove('hidden');
}

function closeVendorModal() {
  document.getElementById('vendor-modal').classList.add('hidden');
}

async function submitVendor() {
  const name    = document.getElementById('v-name').value.trim();
  const contact = document.getElementById('v-contact').value.trim();
  const errEl   = document.getElementById('v-error');
  errEl.classList.add('hidden');

  if (!name || !contact) {
    errEl.textContent = 'Name and Contact are required.';
    errEl.classList.remove('hidden');
    return;
  }

  try {
    await api.post('/vendors', {
      name, contact,
      email:  document.getElementById('v-email').value.trim()   || null,
      phone:  document.getElementById('v-phone').value.trim()   || null,
      rating: parseFloat(document.getElementById('v-rating').value) || 3.0,
    });
    closeVendorModal();
    toast('Vendor added successfully');
    loadVendors();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

// ── Products ──────────────────────────────────────────────────
async function loadProducts() {
  try {
    const products = await api.get('/products?active_only=false');
    if (!products) return;
    const tbody = document.getElementById('products-tbody');
    if (!products.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading-row">No products found.</td></tr>';
      return;
    }
    tbody.innerHTML = products.map(p => `
      <tr>
        <td style="font-weight:500;color:var(--text-primary)">${p.name}</td>
        <td style="font-family:var(--mono);font-size:0.7rem;color:var(--accent)">${p.sku}</td>
        <td>
          <span style="background:var(--bg-hover);padding:2px 8px;border-radius:2px;font-size:0.75rem">
            ${p.category || '—'}
          </span>
        </td>
        <td style="font-family:var(--mono);font-weight:700">${fmt(p.unit_price)}</td>
        <td>
          <span style="color:${p.stock_level < 10 ? 'var(--red)' : p.stock_level < 30 ? 'var(--accent)' : 'var(--green)'}">
            ${p.stock_level}
          </span>
        </td>
        <td style="color:var(--text-muted);font-size:0.75rem">${p.unit_of_measure}</td>
      </tr>`).join('');
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Close modals on overlay click ────────────────────────────
document.querySelectorAll('.modal').forEach(modal => {
  modal.addEventListener('click', e => {
    if (e.target === modal) {
      modal.classList.add('hidden');
    }
  });
});

// ── Handle OAuth callback token in URL ───────────────────────
function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  const name  = params.get('name');
  if (token) {
    // Decode JWT payload to get user info
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const user = { email: payload.email, name: name || payload.name || payload.email, role: payload.role || 'buyer' };
      saveSession(token, user);
      window.history.replaceState({}, '', '/');
      return true;
    } catch (_) {}
  }
  return false;
}

// ── Boot ──────────────────────────────────────────────────────
(function boot() {
  if (handleOAuthCallback()) { showApp(); return; }
  if (loadSession()) { showApp(); return; }
  // Already showing login screen by default
})();
