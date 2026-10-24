let token = localStorage.getItem('eims_token');
// ==================== AVAILABILITY REPORT EXPORTS ====================

async function exportAvailabilityReport(format) {
  const status = $('report-status').value;
  const query = new URLSearchParams({ format });

  if (status) {
    query.set('status', status);
  }

  const feedback = $('report-feedback');

  try {
    feedback.textContent = `Generating ${format.toUpperCase()} report...`;

    const response = await fetch(
      `/api/reports/availability/export?${query.toString()}`,
      {
        headers: token
          ? { Authorization: `Bearer ${token}` }
          : {}
      }
    );

    if (!response.ok) {
      throw new Error('Unable to export the report. Please try again.');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = `availability_report.${format === 'excel' ? 'xlsx' : format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    feedback.textContent = `${format.toUpperCase()} report downloaded successfully.`;
  } catch (error) {
    feedback.textContent = error.message;
  }
}

$('export-pdf').onclick = () => exportAvailabilityReport('pdf');
$('export-excel').onclick = () => exportAvailabilityReport('excel');
$('export-csv').onclick = () => exportAvailabilityReport('csv');
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

  const imageSection = component.image_url
  ? `
    <div class="component-image-section">
      <img
        class="component-image"
        src="${escapeHTML(component.image_url)}"
        alt="${escapeHTML(component.name)}"
        loading="lazy"
      >
    </div>
  `
  : '<p class="no-component-image">No image uploaded yet.</p>';

const imageUploadSection = ['ADMIN', 'MANAGER'].includes(role)
  ? `
    <form id="component-image-form" class="component-image-form">
      <label for="component-image-file">Component image (PNG, JPEG, or WebP; max 5 MB)</label>
      <input
        id="component-image-file"
        name="file"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        required
      >
      <p id="component-image-feedback" class="form-feedback" role="status" aria-live="polite"></p>
      <button type="submit">Upload image</button>
    </form>
  `
  : '';  

  details.innerHTML = `
        ${imageSection}
      ${imageUploadSection}
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
  const imageForm = $('component-image-form');

if (imageForm) {
  imageForm.addEventListener('submit', async event => {
    event.preventDefault();

    const fileInput = $('component-image-file');
    const feedback = $('component-image-feedback');
    const file = fileInput.files[0];

    if (!file) {
      feedback.textContent = 'Please select an image.';
      return;
    }

    const allowedTypes = ['image/png', 'image/jpeg', 'image/webp'];

    if (!allowedTypes.includes(file.type)) {
      feedback.textContent = 'Unsupported format. Please choose a PNG, JPEG, or WebP image.';
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      feedback.textContent = 'Image must be 5 MB or smaller.';
      return;
    }

    const submitButton = imageForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    feedback.textContent = 'Uploading image...';

    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await api(
        `/api/inventory/${component.id}/image`,
        {
          method: 'POST',
          body: formData
        }
      );

      feedback.textContent = result.message || 'Image uploaded successfully.';

      // Reload the component to display its latest saved image.
      currentComponent = await api(`/api/inventory/${component.id}`);
      renderComponentDetails(currentComponent);
    } catch (error) {
      feedback.textContent = `Image upload failed: ${error.message}`;
    } finally {
      submitButton.disabled = false;
    }
  });
}
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

let pendingDeleteComponentId = null;

const deleteConfirmationDialog = $('delete-confirmation-dialog');
const deleteComponentName = $('delete-component-name');
const deleteComponentSku = $('delete-component-sku');
const deleteConfirmationError = $('delete-confirmation-error');
const confirmDeleteButton = $('confirm-delete-component');

function closeDeleteConfirmation() {
if (confirmDeleteButton.disabled) {
return;
}

pendingDeleteComponentId = null;
deleteConfirmationError.textContent = '';
deleteConfirmationDialog.close();
}

window.removeItem = async id => {
if (!['ADMIN', 'MANAGER'].includes(role)) {
alert('You do not have permission to delete components.');
return;
}

try {
const component = await api(`/api/inventory/${id}`);


pendingDeleteComponentId = component.id;
deleteComponentName.textContent = component.name;
deleteComponentSku.textContent = component.sku;
deleteConfirmationError.textContent = '';

deleteConfirmationDialog.showModal();


} catch (error) {
alert(`Unable to load component details: ${error.message}`);
}
};

$('cancel-delete-component').addEventListener(
'click',
closeDeleteConfirmation
);

$('close-delete-confirmation').addEventListener(
'click',
closeDeleteConfirmation
);

deleteConfirmationDialog.addEventListener('click', event => {
if (
event.target === deleteConfirmationDialog &&
!confirmDeleteButton.disabled
) {
closeDeleteConfirmation();
}
});

deleteConfirmationDialog.addEventListener('cancel', event => {
if (confirmDeleteButton.disabled) {
event.preventDefault();
}
});

confirmDeleteButton.addEventListener('click', async () => {
const componentId = pendingDeleteComponentId;

if (componentId === null || confirmDeleteButton.disabled) {
return;
}

confirmDeleteButton.disabled = true;
confirmDeleteButton.textContent = 'Deleting...';
deleteConfirmationError.textContent = '';

try {
await api(`/api/inventory/${componentId}`, {
method: 'DELETE'
});


pendingDeleteComponentId = null;
deleteConfirmationDialog.close();

await refresh();

alert('Component deleted successfully.');


} catch (error) {
deleteConfirmationError.textContent =
`Failed to delete component: ${error.message}`;
} finally {
confirmDeleteButton.disabled = false;
confirmDeleteButton.textContent = 'Confirm Delete';
}
});



// ==================== INITIALIZE APPLICATION ====================

setLoggedIn();