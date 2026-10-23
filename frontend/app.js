
let token = localStorage.getItem('eims_token');
let role = localStorage.getItem('eims_role');

const $ = id => document.getElementById(id);

// API helper
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

// Login and application visibility
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

// Inventory controls
$('refresh').onclick = refresh;
$('search').oninput = refresh;
$('status').onchange = refresh;

// Add-component form visibility
$('add-btn').onclick = () => {
  $('form-card').classList.remove('hidden');
};

$('cancel-add').onclick = () => {
  $('form-card').classList.add('hidden');
  $('form-error').textContent = '';
};

// Add a component
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

// Load and display inventory
async function refresh() {
  if (!token) return;

  try {
    const query = new URLSearchParams();

    if ($('search').value.trim()) {
      query.set('search', $('search').value.trim());
    }

    if ($('status').value) {
      query.set('status', $('status').value);
    }

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

    // Empty inventory state
    if (items.length === 0) {
      $('inventory').innerHTML = `
        <tr>
          <td colspan="9">No inventory components found.</td>
        </tr>
      `;
      return;
    }

    // Inventory table
    $('inventory').innerHTML = items.map(component => {
      const status =
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
          <td class="status">${status}</td>
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
        <td colspan="9">Unable to load inventory. Please try refreshing.</td>
      </tr>
    `;
  }
}

// Escape text returned by the API before inserting it into HTML
function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[character]);
}

// Delete a component (admin/manager only)
window.removeItem = async id => {
  if (!confirm('Delete this component?')) return;

  try {
    await api(`/api/inventory/${id}`, {
      method: 'DELETE'
    });

    await refresh();
  } catch (error) {
    alert(error.message);
  }
};

// Initialize the application
setLoggedIn();