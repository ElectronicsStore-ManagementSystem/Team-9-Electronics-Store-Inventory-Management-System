let token = localStorage.getItem('eims_token');
let role = localStorage.getItem('eims_role');

const $ = id => document.getElementById(id);

// ==================== API HELPER ====================

async function api(path, options = {}) {
  options.headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const response = await fetch(path, options);

  if (!response.ok) {
    let data = {};

    try {
      data = await response.json();
    } catch {
      // Response was not JSON.
    }

    throw new Error(data.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ==================== LOGIN / LOGOUT ====================

function setLoggedIn() {
  $('login-card').classList.toggle('hidden', !!token);
  $('app').classList.toggle('hidden', !token);
  $('logout').classList.toggle('hidden', !token);

  $('add-btn').classList.toggle(
    'hidden',
    !['ADMIN', 'MANAGER'].includes(role)
  );

  if (token) {
    refresh();
  }
}

// Login
$('login-form').onsubmit = async event => {
  event.preventDefault();
  $('login-error').textContent = '';

  try {
    const data = await api('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: $('username').value,
        password: $('password').value
      })
    });

    token = data.access_token;
    role = data.role;

    localStorage.setItem('eims_token', token);
    localStorage.setItem('eims_role', role);

    setLoggedIn();
  } catch (error) {
    $('login-error').textContent = error.message;
  }
};

// Logout
$('logout').onclick = () => {
  token = null;
  role = null;

  localStorage.removeItem('eims_token');
  localStorage.removeItem('eims_role');

  $('login-form').reset();
  $('login-error').textContent = '';
  $('inventory').innerHTML = '';
  $('stats').innerHTML = '';
  $('form-card').classList.add('hidden');

  setLoggedIn();
};

// ==================== INVENTORY CONTROLS ====================

$('refresh').onclick = refresh;
$('search').oninput = refresh;
$('category').onchange = refresh;
$('supplier').onchange = refresh;
$('status').onchange = refresh;

// ==================== ADD COMPONENT FORM ====================

$('add-btn').onclick = () => {
  $('form-card').classList.remove('hidden');
};

$('cancel-add').onclick = () => {
  $('form-card').classList.add('hidden');
  $('form-error').textContent = '';
};

// Add component
$('component-form').onsubmit = async event => {
  event.preventDefault();
  $('form-error').textContent = '';

  const data = Object.fromEntries(
    new FormData(event.target).entries()
  );

  data.quantity = Number(data.quantity);
  data.unit_price = Number(data.unit_price);
  data.reorder_level = Number(data.reorder_level);

  try {
    await api('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    event.target.reset();
    $('form-card').classList.add('hidden');

    await refresh();
  } catch (error) {
    $('form-error').textContent = error.message;
  }
};

// ==================== LOAD AND FILTER INVENTORY ====================

async function refresh() {
  if (!token) return;

  $('inventory').innerHTML = `
    <tr>
      <td colspan="9">Loading inventory...</td>
    </tr>
  `;

  try {
    const query = new URLSearchParams();

    // Search by name, SKU, or category
    const search = $('search').value.trim();

    if (search) {
      query.set('search', search);
    }

    // Filter by category
    const category = $('category').value;

    if (category) {
      query.set('category', category);
    }

    // Filter by supplier
    const supplier = $('supplier').value;

    if (supplier) {
      query.set('supplier', supplier);
    }

    // Filter by stock status
    const statusFilter = $('status').value;

    if (statusFilter) {
      query.set('status', statusFilter);
    }

    // Send all selected filters in one request
    const [items, dashboard] = await Promise.all([
      api('/api/inventory?' + query.toString()),
      api('/api/dashboard')
    ]);

    // Dashboard statistics
    $('stats').innerHTML = `
      <div class="stat">
        Total components
        <b>${dashboard.total_components}</b>
      </div>

      <div class="stat">
        Stock value
        <b>₹${Number(dashboard.total_stock_value).toFixed(2)}</b>
      </div>

      <div class="stat">
        Low stock
        <b>${dashboard.low_stock_count}</b>
      </div>
    `;

    // Handle empty results
    if (!items.length) {
      $('inventory').innerHTML = `
        <tr>
          <td colspan="9">
            No matching components found.
            Try changing or clearing your filters.
          </td>
        </tr>
      `;
      return;
    }

    // Display matching components
    $('inventory').innerHTML = items.map(component => {
      const stockStatus =
        component.quantity === 0
          ? 'out-of-stock'
          : component.quantity <= component.reorder_level
            ? 'low-stock'
            : 'in-stock';

      const action = ['ADMIN', 'MANAGER'].includes(role)
        ? `<button onclick="removeItem(${component.id})">Delete</button>`
        : 'Read only';

      return `
        <tr>
          <td>${escapeHTML(component.sku)}</td>
          <td>${escapeHTML(component.name)}</td>
          <td>${escapeHTML(component.category)}</td>
          <td>${component.quantity}</td>
          <td>₹${Number(component.unit_price).toFixed(2)}</td>
          <td>${escapeHTML(component.supplier)}</td>
          <td>${component.reorder_level}</td>
          <td class="status">${stockStatus}</td>
          <td>${action}</td>
        </tr>
      `;
    }).join('');

  } catch (error) {
    console.error('Failed to load inventory:', error);

    if (
      error.message.includes('401') ||
      error.message.includes('403')
    ) {
      token = null;
      role = null;

      localStorage.removeItem('eims_token');
      localStorage.removeItem('eims_role');

      setLoggedIn();

      $('login-error').textContent =
        'Your session expired. Please log in again.';

      return;
    }

    $('inventory').innerHTML = `
      <tr>
        <td colspan="9">
          Unable to load inventory. Please try refreshing.
        </td>
      </tr>
    `;
  }
}

// ==================== HTML ESCAPING ====================

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[character]);
}

// ==================== DELETE COMPONENT ====================

window.removeItem = async id => {
  if (!confirm('Are you sure you want to delete this component?')) {
    return;
  }

  try {
    await api(`/api/inventory/${id}`, {
      method: 'DELETE'
    });

    await refresh();
  } catch (error) {
    alert(error.message);
  }
};

// ==================== INITIALIZE APPLICATION ====================

setLoggedIn();