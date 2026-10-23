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

    const error = new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `Request failed with status ${response.status}`
    );

    error.status = response.status;
    error.details = Array.isArray(data.detail) ? data.detail : [];

    throw error;
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

const componentFields = [
  'name',
  'category',
  'quantity',
  'unit_price',
  'supplier',
  'reorder_level'
];

const fieldLabels = {
  name: 'Component name',
  category: 'Category',
  quantity: 'Quantity',
  unit_price: 'Unit price',
  supplier: 'Supplier',
  reorder_level: 'Reorder level'
};

function clearFieldErrors() {
  componentFields.forEach(name => {
    const input = document.querySelector(
      `#component-form [name="${name}"]`
    );

    const error = $(`${name}-error`);

    if (input) {
      input.classList.remove('invalid-field');
      input.removeAttribute('aria-invalid');
      input.setCustomValidity('');
    }

    if (error) {
      error.textContent = '';
    }
  });

  $('form-error').textContent = '';
}

function showFieldError(name, message) {
  const input = document.querySelector(
    `#component-form [name="${name}"]`
  );

  const error = $(`${name}-error`);

  if (input) {
    input.classList.add('invalid-field');
    input.setAttribute('aria-invalid', 'true');
    input.setCustomValidity(message);
  }

  if (error) {
    error.textContent = message;
  }
}

function displayValidationErrors(details) {
  let displayedFieldError = false;

  details.forEach(detail => {
    const location = detail.loc || [];
    const fieldName = location[location.length - 1];

    if (!componentFields.includes(fieldName)) {
      return;
    }

    const messages = {
      missing: `${fieldLabels[fieldName]} is required.`,
      string_too_short: `${fieldLabels[fieldName]} cannot be empty.`,
      greater_than_equal:
        `${fieldLabels[fieldName]} must be zero or greater.`,
      int_parsing: `${fieldLabels[fieldName]} must be a whole number.`,
      float_parsing: `${fieldLabels[fieldName]} must be a valid number.`,
      int_type: `${fieldLabels[fieldName]} must be a whole number.`,
      float_type: `${fieldLabels[fieldName]} must be a valid number.`
    };

    showFieldError(
      fieldName,
      messages[detail.type] || detail.msg || 'Please check this field.'
    );

    displayedFieldError = true;
  });

  if (!displayedFieldError) {
    $('form-error').textContent =
      'Please check the component details and try again.';
  } else {
    $('form-error').textContent =
      'Please correct the highlighted fields and try again.';
  }
}

// ==================== ADD COMPONENT FORM ====================

$('add-btn').onclick = () => {
  $('form-card').classList.remove('hidden');
};

$('cancel-add').onclick = () => {
  $('form-card').classList.add('hidden');
  $('form-error').textContent = '';
};

// Add component
// Add component
$('component-form').onsubmit = async event => {
  event.preventDefault();

  clearFieldErrors();

  const form = event.target;

  // Run native browser validation first.
  if (!form.reportValidity()) {
    return;
  }

  const data = Object.fromEntries(
    new FormData(form).entries()
  );

  data.name = data.name.trim();
  data.category = data.category.trim();
  data.supplier = data.supplier.trim();
  data.quantity = Number(data.quantity);
  data.unit_price = Number(data.unit_price);
  data.reorder_level = Number(data.reorder_level);

  // Validate text fields before making an API request.
  let hasErrors = false;

  ['name', 'category', 'supplier'].forEach(name => {
    if (!data[name]) {
      showFieldError(
        name,
        `${fieldLabels[name]} is required.`
      );

      hasErrors = true;
    }
  });

  if (!Number.isInteger(data.quantity) || data.quantity < 0) {
    showFieldError(
      'quantity',
      'Quantity must be a whole number greater than or equal to 0.'
    );

    hasErrors = true;
  }

  if (!Number.isFinite(data.unit_price) || data.unit_price < 0) {
    showFieldError(
      'unit_price',
      'Unit price must be a valid number greater than or equal to 0.'
    );

    hasErrors = true;
  }

  if (
    !Number.isInteger(data.reorder_level) ||
    data.reorder_level < 0
  ) {
    showFieldError(
      'reorder_level',
      'Reorder level must be a whole number greater than or equal to 0.'
    );

    hasErrors = true;
  }

  if (hasErrors) {
    $('form-error').textContent =
      'Please correct the highlighted fields and try again.';

    return;
  }

  try {
    await api('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    form.reset();
    clearFieldErrors();

    $('form-card').classList.add('hidden');

    await refresh();
  } catch (error) {
    if (error.status === 422) {
      displayValidationErrors(error.details);
    } else {
      $('form-error').textContent =
        error.message || 'Unable to save the component. Please try again.';
    }
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