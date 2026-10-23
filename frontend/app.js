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
     const message = Array.isArray(data.detail)
      ? data.detail.map(issue => issue.msg).join(', ')
      : data.detail;

    const error = new Error(
      typeof message === 'string' && message
        ? message
        : `HTTP ${response.status}`
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
  const dateSortOption = $('sort-by').querySelector('[data-admin-only]');
  dateSortOption.hidden = role !== 'ADMIN';
  dateSortOption.disabled = role !== 'ADMIN';

  if (role !== 'ADMIN' && $('sort-by').value === 'date_added') {
    $('sort-by').value = 'id';
  }

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
  $('add-feedback').classList.add('hidden');
  $('add-feedback').textContent = '';

  setLoggedIn();
};

// ==================== INVENTORY CONTROLS ====================

$('refresh').onclick = refresh;
$('search').oninput = refresh;
$('category').onchange = refresh;
$('supplier').onchange = refresh;
$('status').onchange = refresh;
$('sort-by').onchange = refresh;
$('sort-order').onchange = refresh;
$('inventory').addEventListener('click', event => {
  const componentButton = event.target.closest('[data-component-id]');
  if (componentButton) {
    showComponentDetails(componentButton.dataset.componentId);
  }
});
$('component-details').addEventListener('click', event => {
  if (event.target.closest('[data-edit-component]') && currentComponent) {
    renderComponentEditForm(currentComponent);
  }
  if (event.target.closest('[data-cancel-edit]') && currentComponent) {
    renderComponentDetails(currentComponent);
  }
});
$('component-details').addEventListener('submit', async event => {
  if (event.target.id !== 'component-edit-form') return;
  event.preventDefault();

  const form = event.target;
  const errorElement = $('component-edit-error');
  const saveButton = form.querySelector('[type="submit"]');
  errorElement.textContent = '';
  saveButton.disabled = true;
  saveButton.textContent = 'Saving...';

  const formData = new FormData(form);
  const updates = {
    quantity: Number(formData.get('quantity')),
    unit_price: Number(formData.get('unit_price')),
    supplier: String(formData.get('supplier')).trim(),
    reorder_level: Number(formData.get('reorder_level'))
  };

  try {
    const updatedComponent = await api(
      `/api/inventory/${currentComponent.id}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      }
    );

    currentComponent = updatedComponent;
    await refresh();
    renderComponentDetails(currentComponent);
  } catch (error) {
    errorElement.textContent = error.message;
    saveButton.disabled = false;
    saveButton.textContent = 'Save changes';
  }
});
$('close-component-dialog').onclick = () => $('component-dialog').close();
$('component-dialog').addEventListener('click', event => {
  if (event.target === $('component-dialog')) {
    $('component-dialog').close();
  }
});
$('clear-filters').onclick = () => {
  $('search').value = '';
  $('category').value = '';
  $('supplier').value = '';
  $('status').value = '';
  $('sort-by').value = 'id';
  $('sort-order').value = 'asc';
  refresh();
};

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
  $('add-feedback').classList.add('hidden');
  $('add-feedback').textContent = '';
  $('form-card').classList.remove('hidden');
  $('form-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
};

$('cancel-add').onclick = () => {
  $('form-card').classList.add('hidden');
  $('form-error').textContent = '';
};

const addTextFields = {
  name: 'Component name',
  category: 'Category',
  supplier: 'Supplier'
};
for (const fieldName of Object.keys(addTextFields)) {
  $('component-form').elements.namedItem(fieldName).addEventListener(
    'input',
    event => event.target.setCustomValidity('')
  );
}

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

  for (const [fieldName, label] of Object.entries(addTextFields)) {
    const field = form.elements.namedItem(fieldName);
    field.value = field.value.trim();
    field.setCustomValidity(
      field.value ? '' : `${label} is required.`
    );
  }

  if (!form.reportValidity()) {
    return;
  }

  const data = Object.fromEntries(new FormData(form).entries());

  data.name = data.name.trim();
  data.category = data.category.trim();
  data.supplier = data.supplier.trim();
  data.quantity = Number(data.quantity);
  data.unit_price = Number(data.unit_price);
  if (data.reorder_level === '') {
    delete data.reorder_level;
  } else {
    data.reorder_level = Number(data.reorder_level);
  }

  const submitButton = form.querySelector('[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = 'Saving...';

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
    const component = await api('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    form.reset();
    clearFieldErrors();
    
    $('form-card').classList.add('hidden');
    $('add-feedback').textContent =
      `${component.name} added successfully (SKU: ${component.sku}).`;
    $('add-feedback').classList.remove('hidden');

    $('search').value = '';
    $('category').value = '';
    $('supplier').value = '';
    $('status').value = '';
    $('sort-by').value = 'id';
    $('sort-order').value = 'asc';
    await refresh();
  } catch (error) {
    if (error.status === 422) {
      displayValidationErrors(error.details);
    } else {
      $('form-error').textContent =
        error.message || 'Unable to save the component. Please try again.';
    }
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Add component';
  }
};

// ==================== LOAD AND FILTER INVENTORY ====================

let currentComponent = null;

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

    // Sort inventory
    const sortBy = $('sort-by').value;
    const sortOrder = $('sort-order').value;

    query.set(
      'sort',
      sortOrder === 'desc' ? `-${sortBy}` : sortBy
    );

    // Send all selected filters in one request
    const [items, dashboard] = await Promise.all([
      api('/api/inventory?' + query.toString()),
      api('/api/dashboard')
    ]);

    // Dashboard statistics
    $('stats').innerHTML = `
      <div class="stat">
        <span class="stat-icon" aria-hidden="true">#</span>
        <span class="stat-copy">
          <span class="stat-label">Total components</span>
          <b>${dashboard.total_components}</b>
        </span>
      </div>

      <div class="stat">
        <span class="stat-icon" aria-hidden="true">₹</span>
        <span class="stat-copy">
          <span class="stat-label">Stock value</span>
          <b>₹${Number(dashboard.total_stock_value).toFixed(2)}</b>
        </span>
      </div>

      <div class="stat">
        <span class="stat-icon" aria-hidden="true">!</span>
        <span class="stat-copy">
          <span class="stat-label">Low stock items</span>
          <b>${dashboard.low_stock_count}</b>
        </span>
      </div>
    `;

    $('results-count').textContent =
      `${items.length} ${items.length === 1 ? 'item' : 'items'}`;

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

      const statusLabel = {
        'in-stock': 'In stock',
        'low-stock': 'Low stock',
        'out-of-stock': 'Out of stock'
      }[stockStatus];

      const action = ['ADMIN', 'MANAGER'].includes(role)
        ? `<button onclick="removeItem(${component.id})">Delete</button>`
        : 'Read only';

      return `
        <tr>
          <td>${escapeHTML(component.sku)}</td>
          <td>
            <button
              class="component-link"
              type="button"
              data-component-id="${component.id}"
              aria-label="View details for ${escapeHTML(component.name)}"
            >${escapeHTML(component.name)}</button>
          </td>
          <td>${escapeHTML(component.category)}</td>
          <td>${component.quantity}</td>
          <td>₹${Number(component.unit_price).toFixed(2)}</td>
          <td>${escapeHTML(component.supplier)}</td>
          <td>${component.reorder_level}</td>
          <td><span class="status-badge status-${stockStatus}">${statusLabel}</span></td>
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

async function showComponentDetails(componentId) {
  const dialog = $('component-dialog');
  const details = $('component-details');
  currentComponent = null;
  details.innerHTML = '<p class="details-message">Loading component details...</p>';
  dialog.showModal();

  try {
    currentComponent = await api(`/api/inventory/${componentId}`);
    renderComponentDetails(currentComponent);
  } catch (error) {
    console.error('Failed to load component details:', error);
    details.innerHTML = `
      <p class="details-error" role="alert">
        Unable to load component details. ${escapeHTML(error.message)}
      </p>
    `;
  }
}

function renderComponentDetails(component) {
  const details = $('component-details');
  const stockStatus = component.quantity === 0
      ? 'out-of-stock'
      : component.quantity <= component.reorder_level
        ? 'low-stock'
        : 'in-stock';
  const statusLabel = {
    'in-stock': 'In stock',
    'low-stock': 'Low stock',
    'out-of-stock': 'Out of stock'
  }[stockStatus];
  const dateAdded = role === 'ADMIN' && component.created_at
      ? `
        <div class="detail-item">
          <dt>Date added</dt>
          <dd>${escapeHTML(new Intl.DateTimeFormat(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short'
          }).format(new Date(component.created_at)))}</dd>
        </div>
      `
      : '';
  const editButton = ['ADMIN', 'MANAGER'].includes(role)
    ? '<button class="details-edit-button" type="button" data-edit-component>Edit details</button>'
    : '';

  details.innerHTML = `
    <p class="component-detail-category">${escapeHTML(component.category)}</p>
    <dl class="details-grid">
      <div class="detail-item detail-name">
        <dt>Component</dt>
        <dd>${escapeHTML(component.name)}</dd>
      </div>
      <div class="detail-item">
        <dt>SKU</dt>
        <dd>${escapeHTML(component.sku)}</dd>
      </div>
      <div class="detail-item">
        <dt>Stock status</dt>
        <dd><span class="status-badge status-${stockStatus}">${statusLabel}</span></dd>
      </div>
      <div class="detail-item">
        <dt>Quantity in stock</dt>
        <dd>${component.quantity}</dd>
      </div>
      <div class="detail-item">
        <dt>Unit price</dt>
        <dd>₹${Number(component.unit_price).toFixed(2)}</dd>
      </div>
      <div class="detail-item">
        <dt>Supplier</dt>
        <dd>${escapeHTML(component.supplier)}</dd>
      </div>
      <div class="detail-item">
        <dt>Reorder level</dt>
        <dd>${component.reorder_level}</dd>
      </div>
      ${dateAdded}
    </dl>
    ${editButton}
  `;
}

function renderComponentEditForm(component, errorMessage = '') {
  $('component-details').innerHTML = `
    <form id="component-edit-form" class="component-edit-form">
      <label>
        Quantity
        <input name="quantity" type="number" min="0" step="1" value="${component.quantity}" required>
      </label>
      <label>
        Unit price (₹)
        <input name="unit_price" type="number" min="0" step="0.01" value="${component.unit_price}" required>
      </label>
      <label>
        Supplier
        <input name="supplier" type="text" maxlength="120" value="${escapeHTML(component.supplier)}" required>
      </label>
      <label>
        Reorder level
        <input name="reorder_level" type="number" min="0" step="1" value="${component.reorder_level}" required>
      </label>
      <p id="component-edit-error" class="details-error" role="alert">${escapeHTML(errorMessage)}</p>
      <div class="component-edit-actions">
        <button class="secondary-button" type="button" data-cancel-edit>Cancel</button>
        <button type="submit">Save changes</button>
      </div>
    </form>
  `;
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