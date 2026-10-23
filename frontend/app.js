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
    throw new Error(message || `HTTP ${response.status}`);
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
  const isStaff = role === 'STAFF';
  $('dashboard-role').textContent = isStaff
    ? 'Staff · Read-only view'
    : `${role === 'ADMIN' ? 'Admin' : 'Manager'} · Full view`;
  $('dashboard-description').textContent = isStaff
    ? 'Review inventory, stock levels, and suppliers. Changes require a manager.'
    : 'Track and manage components, stock levels, and suppliers.';
  $('quick-start-add-step').innerHTML = ['ADMIN', 'MANAGER'].includes(role)
    ? '<strong>Add it:</strong> choose <strong>Add component</strong> and complete the form.'
    : '<strong>Add it:</strong> ask a manager to add new stock; you can search and review components here.';

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
  $('recent-components-list').innerHTML = '';
  $('category-chart').innerHTML = '';
  $('trend-chart').innerHTML = '';
  $('low-stock-alert').classList.add('hidden');
  $('low-stock-alert-items').innerHTML = '';
  $('form-card').classList.add('hidden');
  $('add-feedback').classList.add('hidden');
  $('add-feedback').textContent = '';

  setLoggedIn();
};

// ==================== INVENTORY CONTROLS ====================

$('refresh').onclick = refresh;
let searchTimer;
$('search').oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refresh, 300);
};
$('search').onkeydown = event => {
  if (event.key === 'Enter') {
    event.preventDefault();
    clearTimeout(searchTimer);
    refresh();
  }
};
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
$('recent-components-list').addEventListener('click', event => {
  const componentButton = event.target.closest('[data-component-id]');
  if (componentButton) {
    showComponentDetails(componentButton.dataset.componentId);
  }
});
$('low-stock-alert-items').addEventListener('click', event => {
  const componentButton = event.target.closest('[data-component-id]');
  if (componentButton) {
    showComponentDetails(componentButton.dataset.componentId);
  }
});
$('view-low-stock').onclick = () => {
  $('search').value = '';
  $('status').value = 'low-stock';
  refresh();
  $('inventory').scrollIntoView({ behavior: 'smooth', block: 'start' });
};
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

// ==================== ADD COMPONENT FORM ====================

$('add-btn').onclick = () => {
  $('add-feedback').classList.add('hidden');
  $('add-feedback').textContent = '';
  $('form-card').classList.remove('hidden');
  $('form-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
  $('component-form').elements.namedItem('name').focus();
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
$('component-form').onsubmit = async event => {
  event.preventDefault();
  $('form-error').textContent = '';

  const form = event.target;
  for (const [fieldName, label] of Object.entries(addTextFields)) {
    const field = form.elements.namedItem(fieldName);
    field.value = field.value.trim();
    field.setCustomValidity(
      field.value ? '' : `${label} is required.`
    );
  }

  if (!form.reportValidity()) return;

  const data = Object.fromEntries(new FormData(form).entries());

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

  try {
    const component = await api('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    form.reset();
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
    $('form-error').textContent = error.message;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Save component';
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

    const recentComponents = dashboard.recently_added || [];
    $('recent-components-list').innerHTML = recentComponents.length
      ? recentComponents.map(component => `
          <button
            class="recent-component"
            type="button"
            data-component-id="${component.id}"
            aria-label="View recently added ${escapeHTML(component.name)}"
          >
            <span class="recent-component-name">${escapeHTML(component.name)}</span>
            <span class="recent-component-meta">
              ${escapeHTML(component.category)} · ${escapeHTML(component.sku)}
            </span>
          </button>
        `).join('')
      : '<p class="empty-state">No components have been added yet.</p>';
    renderLowStockAlert(dashboard);
    renderBarChart(
      $('category-chart'),
      dashboard.category_stock || [],
      item => item.category,
      item => item.quantity,
      'category'
    );
    renderBarChart(
      $('trend-chart'),
      dashboard.stock_trend || [],
      item => item.date,
      item => item.quantity,
      'date'
    );

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

    function renderLowStockAlert(dashboard) {
      const count = dashboard.low_stock_count || 0;
      const components = dashboard.low_stock_components || [];
      const alert = $('low-stock-alert');

      if (!count) {
        alert.classList.add('hidden');
        return;
      }

      $('low-stock-alert-message').textContent =
        `${count} ${count === 1 ? 'component is' : 'components are'} at or below the reorder level.`;
      $('low-stock-alert-items').innerHTML = components.map(component => `
        <button
          class="low-stock-alert-item"
          type="button"
          data-component-id="${component.id}"
          aria-label="View low-stock ${escapeHTML(component.name)}"
        >
          ${escapeHTML(component.name)}
          <span>${component.quantity} / ${component.reorder_level} units</span>
        </button>
      `).join('');
      alert.classList.remove('hidden');
    }

    function renderBarChart(container, points, label, value, kind) {
      if (!points.length) {
        container.innerHTML = '<p class="empty-state">Not enough data to chart yet.</p>';
        return;
      }

      const maximum = Math.max(...points.map(value), 1);
      container.innerHTML = points.map(point => {
        const amount = value(point);
        const width = Math.max((amount / maximum) * 100, amount ? 4 : 0);
        const displayLabel = kind === 'date'
          ? new Intl.DateTimeFormat(undefined, {
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            }).format(new Date(`${label(point)}T00:00:00`))
          : label(point);
        return `
          <div class="chart-row">
            <span class="chart-label" title="${escapeHTML(displayLabel)}">${escapeHTML(displayLabel)}</span>
            <span class="chart-track">
              <span class="chart-bar" style="width: ${width}%"></span>
            </span>
            <strong class="chart-value">${amount}</strong>
          </div>
        `;
      }).join('');
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
        ? `<button class="management-control" onclick="removeItem(${component.id})">Delete</button>`
        : '<span class="read-only-label">Read only</span>';

      return `
        <tr class="stock-row-${stockStatus}">
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
          <td class="quantity-cell">
            <span>${component.quantity}</span>
            ${stockStatus === 'low-stock'
              ? '<span class="stock-alert">Needs reorder</span>'
              : ''}
          </td>
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