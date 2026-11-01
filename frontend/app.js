let token = localStorage.getItem('eims_token');
let role = localStorage.getItem('eims_role');
let availableBranches = [];

const $ = id => document.getElementById(id);

function applyTheme(theme) {
  const isDark = theme === 'dark';
  document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
  $('theme-toggle').textContent = isDark ? 'Light mode' : 'Dark mode';
  $('theme-toggle').setAttribute('aria-pressed', String(isDark));
  $('theme-toggle').setAttribute(
    'aria-label',
    `Switch to ${isDark ? 'light' : 'dark'} mode`
  );
  localStorage.setItem('eims_theme', isDark ? 'dark' : 'light');
}

const savedTheme = localStorage.getItem('eims_theme');
const initialTheme = savedTheme === 'dark' || savedTheme === 'light'
  ? savedTheme
  : window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
applyTheme(initialTheme);
$('theme-toggle').onclick = () => {
  applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
};

// ==================== AVAILABILITY REPORT EXPORTS =============
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


// ==================== API HELPER =============
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


// ==================== LOGIN / LOGOUT =============
function setLoggedIn() {
  $('login-card').classList.toggle('hidden', !!token);
  $('app').classList.toggle('hidden', !token);
  $('logout').classList.toggle('hidden', !token);
  $('availability-report').classList.toggle('hidden', role !== 'ADMIN');
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
  $('supplier-btn').classList.toggle(
    'hidden',
    !['ADMIN', 'MANAGER'].includes(role)
  );
  $('branch-btn').classList.toggle(
    'hidden',
    !['ADMIN', 'MANAGER'].includes(role)
  );
  $('create-purchase-order-btn').classList.toggle(
    'hidden',
    !['ADMIN', 'MANAGER'].includes(role)
  );
  const isStaff = role === 'STAFF';
  $('dashboard-role').textContent = isStaff
    ? 'Staff · Read-only view'
    : `${role === 'ADMIN' ? 'Admin' : 'Manager'} · Full view`;
  $('dashboard-description').textContent = isStaff
    ? 'Review inventory, stock levels, and shop branches. Changes require a manager.'
    : 'Track components and manage stock across shop branches.';
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
  $('purchase-orders-section').classList.add('hidden');
  $('purchase-orders-list').replaceChildren();
  $('purchase-orders-feedback').textContent = '';
  if ($('form-card').open) $('form-card').close();
  if ($('branch-card').open) $('branch-card').close();
  if ($('purchase-order-dialog').open) $('purchase-order-dialog').close();
  $('add-feedback').classList.add('hidden');
  $('add-feedback').textContent = '';

  setLoggedIn();
};

$('refresh').onclick = refresh;
let searchTimer;
let searchRefreshTimer;
$('search-results-list').addEventListener('click', event => {
  const componentButton = event.target.closest('[data-component-id]');
  if (componentButton) {
    showComponentDetails(componentButton.dataset.componentId);
  }
});
$('search-results-list').addEventListener('keydown', event => {
  const suggestions = [...$('search-results-list').querySelectorAll('[role="option"]')];
  const currentIndex = suggestions.indexOf(document.activeElement);

  if (event.key === 'ArrowDown' && currentIndex < suggestions.length - 1) {
    event.preventDefault();
    suggestions[currentIndex + 1].focus();
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    if (currentIndex <= 0) {
      $('search').focus();
    } else {
      suggestions[currentIndex - 1].focus();
    }
  } else if (event.key === 'Escape') {
    event.preventDefault();
    $('search').focus();
  }
});

function updateSearchView() {
  const search = $('search').value.trim();
  const isSearching = search.length > 0;
  $('app').classList.toggle('search-active', isSearching);
  $('search-results').classList.toggle('hidden', !isSearching);
  $('search').setAttribute('aria-expanded', String(isSearching));

  if (!isSearching) {
    clearInterval(searchRefreshTimer);
    $('search-results-status').textContent = '';
    $('search-results-list').replaceChildren();
    return;
  }

  $('search-results-status').textContent = 'Searching inventory...';
  clearInterval(searchRefreshTimer);
  searchRefreshTimer = setInterval(() => {
    if (token && $('search').value.trim()) {
      refresh();
    }
  }, 5000);
}

function updateFilterView() {
  const hasActiveFilter = ['category', 'supplier', 'branch', 'status']
    .some(id => $(id).value !== '');
  $('app').classList.toggle('filter-active', hasActiveFilter);
}

$('search').oninput = () => {
  updateSearchView();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refresh, 300);
};
$('search').onkeydown = event => {
  if (event.key === 'ArrowDown') {
    const firstSuggestion = $('search-results-list').querySelector(
      '[role="option"]'
    );
    if (firstSuggestion) {
      event.preventDefault();
      firstSuggestion.focus();
    }
    return;
  }

  if (event.key === 'Enter') {
    event.preventDefault();
    clearTimeout(searchTimer);
    updateSearchView();
    refresh();
  }
};
$('category').onchange = () => {
  updateFilterView();
  refresh();
};
$('supplier').onchange = () => {
  updateFilterView();
  refresh();
};
$('branch').onchange = () => {
  updateFilterView();
  refresh();
};
$('status').onchange = () => {
  updateFilterView();
  refresh();
};
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
  document.querySelector('.filter-panel').open = true;
  updateSearchView();
  updateFilterView();
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
  if (event.target.closest('[data-refresh-movements]') && currentComponent) {
    loadStockMovementHistory(currentComponent.id);
  }
});
$('component-details').addEventListener('submit', async event => {
  if (event.target.id === 'stock-movement-form') {
    event.preventDefault();
    await submitStockMovement(event.target);
    return;
  }
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
    unit_price: Number(formData.get('unit_price')),
    supplier: String(formData.get('supplier')).trim(),
    branch: String(formData.get('branch')).trim(),
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
$('component-dialog').addEventListener('cancel', event => {
  event.preventDefault();
  $('component-dialog').close();
});
$('component-dialog').addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    event.preventDefault();
    $('component-dialog').close();
  }
});
$('component-dialog').addEventListener('click', event => {
  if (event.target === $('component-dialog')) {
    $('component-dialog').close();
  }
});
$('clear-filters').onclick = () => {
  $('search').value = '';
  $('category').value = '';
  $('supplier').value = '';
  $('branch').value = '';
  $('status').value = '';
  $('sort-by').value = 'id';
  $('sort-order').value = 'asc';
  updateSearchView();
  updateFilterView();
  refresh();
};

$('supplier-btn').onclick = () => {
  $('supplier-feedback').classList.add('hidden');
  $('supplier-feedback').textContent = '';
  $('supplier-error').textContent = '';
  $('supplier-card').showModal();
  $('supplier-name').focus();
};

$('cancel-supplier').onclick = () => {
  $('supplier-form').reset();
  $('supplier-error').textContent = '';
  $('supplier-card').close();
};

$('supplier-card').addEventListener('click', event => {
  if (event.target === $('supplier-card')) {
    $('supplier-card').close();
  }
});

$('supplier-card').addEventListener('close', () => {
  $('supplier-form').reset();
  $('supplier-error').textContent = '';
});

$('supplier-name').addEventListener('input', event => {
  event.target.setCustomValidity('');
});

$('supplier-form').onsubmit = async event => {
  event.preventDefault();
  const form = event.target;
  const nameInput = $('supplier-name');
  const name = nameInput.value.trim();
  const submitButton = form.querySelector('[type="submit"]');
  $('supplier-error').textContent = '';
  $('supplier-feedback').classList.add('hidden');

  if (!name) {
    nameInput.setCustomValidity('Supplier name is required.');
    nameInput.reportValidity();
    return;
  }

  nameInput.setCustomValidity('');
  submitButton.disabled = true;
  submitButton.textContent = 'Saving...';

  try {
    const supplier = await api('/api/suppliers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    form.reset();
    $('supplier-feedback').textContent = `${supplier.name} added successfully.`;
    $('supplier-feedback').classList.remove('hidden');
    await refresh();
  } catch (error) {
    $('supplier-error').textContent = error.message;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Add supplier';
  }
};

$('supplier-name').addEventListener('input', event => {
  event.target.setCustomValidity('');
});

$('branch-btn').onclick = () => {
  $('branch-feedback').classList.add('hidden');
  $('branch-feedback').textContent = '';
  $('branch-management-error').textContent = '';
  $('branch-card').showModal();
  $('branch-name').focus();
};

$('cancel-branch').onclick = () => {
  $('branch-form').reset();
  $('branch-card').close();
  $('branch-management-error').textContent = '';
};

$('branch-card').addEventListener('click', event => {
  if (event.target === $('branch-card')) {
    $('branch-card').close();
  }
});

$('branch-form').onsubmit = async event => {
  event.preventDefault();
  const form = event.target;
  const nameInput = $('branch-name');
  const name = nameInput.value.trim();
  const submitButton = form.querySelector('[type="submit"]');
  $('branch-management-error').textContent = '';
  $('branch-feedback').classList.add('hidden');

  if (!name) {
    nameInput.setCustomValidity('Branch or area name is required.');
    nameInput.reportValidity();
    return;
  }

  nameInput.setCustomValidity('');
  submitButton.disabled = true;
  submitButton.textContent = 'Saving...';

  try {
    const branch = await api('/api/branches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    form.reset();
    $('branch-feedback').textContent = `${branch.name} added successfully.`;
    $('branch-feedback').classList.remove('hidden');
    await refresh();
  } catch (error) {
    $('branch-management-error').textContent = error.message;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Add branch';
  }
};

$('branch-name').addEventListener('input', event => {
  event.target.setCustomValidity('');
});
const componentFields = [
  'name',
  'category',
  'quantity',
  'unit_price',
  'supplier',
  'branch',
  'reorder_level'
];

const fieldLabels = {
  name: 'Component name',
  category: 'Category',
  quantity: 'Quantity',
  unit_price: 'Unit price',
  supplier: 'Supplier',
  branch: 'Shop branch',
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

// ==================== ADD COMPONENT FORM =============
$('add-btn').onclick = () => {
  $('add-feedback').classList.add('hidden');
  $('add-feedback').textContent = '';
  $('form-card').showModal();
  $('component-form').elements.namedItem('name').focus();
};

$('cancel-add').onclick = () => {
  $('component-form').reset();
  clearFieldErrors();
  $('form-card').close();
};
$('form-card').addEventListener('click', event => {
  if (event.target === $('form-card')) {
    $('form-card').close();
  }
});
$('form-card').addEventListener('close', () => {
  $('component-form').reset();
  clearFieldErrors();
});
$('branch-card').addEventListener('close', () => {
  $('branch-form').reset();
  $('branch-management-error').textContent = '';
});

const addTextFields = {
  name: 'Component name',
  category: 'Category',
  supplier: 'Supplier',
  branch: 'Shop branch'
};
for (const fieldName of Object.keys(addTextFields)) {
  const eventName = ['supplier', 'branch'].includes(fieldName) ? 'change' : 'input';
  $('component-form').elements.namedItem(fieldName).addEventListener(
    eventName,
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

  submitButton.disabled = true;
  submitButton.textContent = 'Saving...';

  try {
    const component = await api('/api/inventory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    form.reset();
    clearFieldErrors();
    
    $('form-card').close();
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

// ==================== LOAD AND FILTER INVENTORY =============
let currentComponent = null;
let availableSuppliers = [];
let refreshRequestId = 0;

function populateSelect(select, values, placeholder) {
  const selectedValue = select.value;
  select.replaceChildren();

  const defaultOption = document.createElement('option');
  defaultOption.value = '';
  defaultOption.textContent = placeholder;
  select.append(defaultOption);

  values.forEach(value => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.append(option);
  });

  select.value = values.includes(selectedValue) ? selectedValue : '';
}

function renderSupplierList(suppliers) {
  const list = $('supplier-list');
  list.replaceChildren();

  if (!suppliers.length) {
    const item = document.createElement('li');
    item.className = 'empty-state';
    item.textContent = 'No suppliers have been added yet.';
    list.append(item);
    return;
  }

  suppliers.forEach(supplier => {
    const item = document.createElement('li');
    item.textContent = supplier;
    list.append(item);
  });
}

function renderBranchList(branches) {
  const list = $('branch-list');
  list.replaceChildren();

  if (!branches.length) {
    const item = document.createElement('li');
    item.className = 'empty-state';
    item.textContent = 'No branches have been added yet.';
    list.append(item);
    return;
  }

  branches.forEach(branch => {
    const item = document.createElement('li');
    item.textContent = branch;
    list.append(item);
  });
}

async function refresh() {
  if (!token) return;
  const requestId = ++refreshRequestId;

  $('inventory').innerHTML = `
    <tr>
      <td colspan="10">Loading inventory...</td>
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

    const branch = $('branch').value;
    if (branch) {
      query.set('branch', branch);
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
    const [items, dashboard, categories, suppliers, branches] = await Promise.all([
      api('/api/inventory?' + query.toString()),
      api('/api/dashboard'),
      api('/api/categories'),
      api('/api/suppliers'),
      api('/api/branches')
    ]);

    if (
      requestId !== refreshRequestId ||
      $('search').value.trim() !== search
    ) {
      return;
    }

    availableSuppliers = suppliers;
    availableBranches = branches;
    populateSelect($('category'), categories, 'All categories');
    populateSelect($('supplier'), suppliers, 'All suppliers');
    populateSelect($('branch'), branches, 'All branches');
    populateSelect(
      $('component-form').elements.namedItem('supplier'),
      suppliers,
      'Choose a supplier'
    );
    renderSupplierList(suppliers);
    populateSelect(
      $('component-form').elements.namedItem('branch'),
      branches,
      'Choose a branch'
    );
    renderBranchList(branches);

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
    renderSearchResults(items);

    // Handle empty results
    if (!items.length) {
      $('inventory').innerHTML = `
        <tr>
          <td colspan="10">
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
          <td>${escapeHTML(component.branch)}</td>
          <td>${component.reorder_level}</td>
          <td><span class="status-badge status-${stockStatus}">${statusLabel}</span></td>
          <td>${action}</td>
        </tr>
      `;
    }).join('');

  } catch (error) {
    if (requestId !== refreshRequestId) return;
    console.error('Failed to load inventory:', error);
    if ($('search').value.trim()) {
      $('search-results-status').textContent =
        'Unable to search inventory. Please try again.';
    }

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
        <td colspan="10">
          Unable to load inventory. Please try refreshing.
        </td>
      </tr>
    `;
  }
}

function renderSearchResults(items) {
  const search = $('search').value.trim();
  if (!search) return;

  const status = $('search-results-status');
  const list = $('search-results-list');
  status.textContent = items.length
    ? `${items.length} ${items.length === 1 ? 'matching component' : 'matching components'}`
    : 'No matching components found.';

  list.innerHTML = items.map(component => `
    <button
      class="search-result"
      type="button"
      role="option"
      aria-selected="false"
      data-component-id="${component.id}"
      aria-label="View ${escapeHTML(component.name)}, SKU ${escapeHTML(component.sku)}"
    >
      <span class="search-result-heading">
        <strong>${escapeHTML(component.name)}</strong>
        <span>${escapeHTML(component.sku)}</span>
      </span>
      <span class="search-result-details">
        ${escapeHTML(component.category)} · ${escapeHTML(component.supplier)}
      </span>
      <span class="search-result-stock">
        ${escapeHTML(component.branch)}
      </span>
      <span class="search-result-stock">
        ${component.quantity} in stock · ₹${Number(component.unit_price).toFixed(2)}
      </span>
    </button>
  `).join('');
}

async function showComponentDetails(componentId) {
  const dialog = $('component-dialog');
  const details = $('component-details');
  currentComponent = null;
  stockMovementFeedback = '';
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

let stockMovementFeedback = '';

async function loadStockMovementHistory(componentId) {
  const historyList = $('stock-movement-history-list');
  if (!historyList) return;
  historyList.innerHTML = '<p class="details-message">Loading movement history...</p>';

  try {
    const movements = await api(`/api/inventory/${componentId}/movements`);
    if (
      !currentComponent ||
      currentComponent.id !== componentId ||
      !document.querySelector('#stock-movement-history-list')
    ) {
      return;
    }

    const activeHistoryList = $('stock-movement-history-list');
    activeHistoryList.innerHTML = movements.length
      ? `
        <ol class="stock-movement-list" aria-label="Recorded stock movements">
          ${movements.map(movement => {
            const isStockIn = movement.movement_type === 'STOCK_IN';
            const recordedAt = new Intl.DateTimeFormat(undefined, {
              dateStyle: 'medium',
              timeStyle: 'short'
            }).format(new Date(movement.timestamp));
            return `
              <li class="stock-movement-entry">
                <div class="stock-movement-entry-heading">
                  <span class="stock-movement-badge ${isStockIn ? 'stock-movement-in' : 'stock-movement-out'}">
                    ${isStockIn ? 'Stock In' : 'Stock Out'}
                  </span>
                  <strong class="stock-movement-quantity ${isStockIn ? 'quantity-in' : 'quantity-out'}">
                    ${isStockIn ? '+' : '−'}${movement.quantity} <span>units</span>
                  </strong>
                </div>
                <dl class="stock-movement-meta">
                  <div class="stock-movement-reason">
                    <dt>Reason</dt>
                    <dd>${escapeHTML(movement.reason)}</dd>
                  </div>
                  <div>
                    <dt>Date &amp; time</dt>
                    <dd><time datetime="${escapeHTML(movement.timestamp)}">${escapeHTML(recordedAt)}</time></dd>
                  </div>
                  <div>
                    <dt>Recorded by</dt>
                    <dd>${escapeHTML(movement.actor_role.charAt(0) + movement.actor_role.slice(1).toLowerCase())}</dd>
                  </div>
                </dl>
              </li>
            `;
          }).join('')}
        </ol>
      `
      : `
        <div class="stock-movement-empty">
          <strong>No movement history yet</strong>
          <p>Stock additions and deductions for this component will appear here.</p>
        </div>
      `;
  } catch (error) {
    if (currentComponent && currentComponent.id === componentId) {
      const activeHistoryList = $('stock-movement-history-list');
      if (activeHistoryList) {
        activeHistoryList.innerHTML = `
          <p class="details-error" role="alert">
            Unable to load stock movement history. ${escapeHTML(error.message)}
          </p>
        `;
      }
    }
  }
}

async function submitStockMovement(form) {
  if (!currentComponent) return;

  const errorElement = $('stock-movement-error');
  const feedback = $('stock-movement-feedback');
  const submitButton = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  const movementType = String(formData.get('movement_type'));
  const quantity = Number(formData.get('quantity'));
  const reason = String(formData.get('reason')).trim();
  errorElement.textContent = '';
  feedback.textContent = '';

  if (!Number.isInteger(quantity) || quantity <= 0) {
    errorElement.textContent = 'Quantity must be a positive whole number.';
    return;
  }
  if (!reason) {
    errorElement.textContent = 'Enter a reason for this stock movement.';
    return;
  }
  if (movementType === 'STOCK_OUT' && quantity > currentComponent.quantity) {
    errorElement.textContent =
      `Only ${currentComponent.quantity} unit${currentComponent.quantity === 1 ? '' : 's'} available.`;
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = 'Recording...';

  try {
    await api(`/api/inventory/${currentComponent.id}/movements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        movement_type: movementType,
        quantity,
        reason
      })
    });

    currentComponent.quantity +=
      movementType === 'STOCK_IN' ? quantity : -quantity;
    stockMovementFeedback =
      `${movementType === 'STOCK_IN' ? 'Stock added' : 'Stock deducted'} successfully.`;
    renderComponentDetails(currentComponent);
    await refresh();
  } catch (error) {
    errorElement.textContent = error.message;
    submitButton.disabled = false;
    submitButton.textContent = 'Record movement';
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
  const movementForm = ['ADMIN', 'MANAGER'].includes(role)
    ? `
      <form id="stock-movement-form" class="stock-movement-form">
        <div class="stock-movement-form-heading">
          <div class="stock-movement-section-icon" aria-hidden="true">↕</div>
          <div>
            <h3>Record stock movement</h3>
            <p>Every adjustment is saved to this component's movement history.</p>
          </div>
        </div>
        <div class="stock-movement-fields">
          <label>
            Movement
            <select name="movement_type" required>
              <option value="STOCK_IN">Stock In</option>
              <option value="STOCK_OUT">Stock Out</option>
            </select>
          </label>
          <label>
            Quantity
            <input name="quantity" type="number" min="1" step="1" required placeholder="Units">
          </label>
          <label class="stock-movement-reason">
            Reason
            <input name="reason" type="text" maxlength="500" required placeholder="e.g. Supplier delivery or customer sale">
          </label>
        </div>
        <p id="stock-movement-feedback" class="form-feedback" role="status" aria-live="polite">${escapeHTML(stockMovementFeedback)}</p>
        <p id="stock-movement-error" class="details-error" role="alert"></p>
        <div class="stock-movement-form-actions">
          <button type="submit">Record movement</button>
        </div>
      </form>
    `
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
        <label for="component-image-file">
          ${component.image_url ? 'Replace component image' : 'Upload component image'}
          (PNG, JPEG, or WebP; max 5 MB)
        </label>
        <input
          id="component-image-file"
          name="file"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          required
        >
        <p id="component-image-feedback" class="form-feedback" role="status" aria-live="polite"></p>
        <div class="component-image-actions">
          <button type="submit">Upload image</button>
          ${component.image_url ? '<button type="button" id="remove-component-image" class="danger-button">Remove image</button>' : ''}
        </div>
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
        <dt>Shop branch</dt>
        <dd>${escapeHTML(component.branch)}</dd>
      </div>
      <div class="detail-item">
        <dt>Reorder level</dt>
        <dd>${component.reorder_level}</dd>
      </div>
      ${dateAdded}
    </dl>
    ${editButton}
    ${movementForm}
    <section class="stock-movement-history" aria-labelledby="stock-movement-history-title">
      <div class="stock-movement-history-heading">
        <div>
          <h3 id="stock-movement-history-title">Stock movement history</h3>
          <p>Every recorded change, newest first.</p>
        </div>
        <button class="secondary-button" type="button" data-refresh-movements aria-label="Refresh stock movement history">
          <span aria-hidden="true">↻</span> Refresh
        </button>
      </div>
      <div id="stock-movement-history-list" class="stock-movement-history-list" aria-live="polite">
        <p class="details-message">Loading movement history...</p>
      </div>
    </section>
  `;
  loadStockMovementHistory(component.id);
  const imageForm = $('component-image-form');

  const removeImageButton = $('remove-component-image');

if (removeImageButton) {
  removeImageButton.addEventListener('click', async () => {
    const feedback = $('component-image-feedback');

    removeImageButton.disabled = true;
    feedback.textContent = 'Removing image...';

    try {
      const result = await api(
        `/api/inventory/${component.id}/image`,
        { method: 'DELETE' }
      );

      currentComponent = await api(`/api/inventory/${component.id}`);
      renderComponentDetails(currentComponent);

      const updatedFeedback = $('component-image-feedback');
      if (updatedFeedback) {
        updatedFeedback.textContent = result.message || 'Image removed successfully.';
      }
    } catch (error) {
      feedback.textContent = `Image removal failed: ${error.message}`;
      removeImageButton.disabled = false;
    }
  });
}

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

      // Reload the component to display its latest saved image.
      currentComponent = await api(`/api/inventory/${component.id}`);
      renderComponentDetails(currentComponent);

      const updatedFeedback = $('component-image-feedback');
      if (updatedFeedback) {
        updatedFeedback.textContent = result.message || 'Image uploaded successfully.';
      }
    } catch (error) {
      feedback.textContent = `Image upload failed: ${error.message}`;
    } finally {
      submitButton.disabled = false;
    }
  });
}
}

function renderComponentEditForm(component, errorMessage = '') {
  const supplierOptions = availableSuppliers.map(supplier => `
    <option value="${escapeHTML(supplier)}"${supplier === component.supplier ? ' selected' : ''}>
      ${escapeHTML(supplier)}
    </option>
  `).join('');
  const branchOptions = availableBranches.map(branch => `
    <option value="${escapeHTML(branch)}"${branch === component.branch ? ' selected' : ''}>
      ${escapeHTML(branch)}
    </option>
  `).join('');
  $('component-details').innerHTML = `
    <form id="component-edit-form" class="component-edit-form">
      <label>
        Unit price (₹)
        <input name="unit_price" type="number" min="0" step="0.01" value="${component.unit_price}" required>
      </label>
      <label>
        Supplier
        <select name="supplier" required>
          <option value="">Choose a supplier</option>
          ${supplierOptions}
        </select>
      </label>
      <label>
        Shop branch
        <select name="branch" required>
          <option value="">Choose a branch</option>
          ${branchOptions}
        </select>
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

// ==================== PURCHASE ORDERS =============
let purchaseOrderSuppliers = [];
let purchaseOrderComponents = [];
let purchaseOrders = [];

function openPurchaseOrders() {
  $('search').value = '';
  updateSearchView();
  $('purchase-orders-section').classList.remove('hidden');
  $('purchase-orders-section').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });
  loadPurchaseOrders();
}

function closePurchaseOrders() {
  $('purchase-orders-section').classList.add('hidden');
  $('inventory-section').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });
}

async function loadPurchaseOrders() {
  const refreshButton = $('refresh-purchase-orders');
  refreshButton.disabled = true;
  $('purchase-orders-feedback').textContent = 'Loading purchase orders...';

  try {
    const [orders, suppliers, components] = await Promise.all([
      api('/api/purchase-orders'),
      api('/api/suppliers/catalog'),
      api('/api/inventory?limit=500')
    ]);

    purchaseOrders = orders;
    purchaseOrderSuppliers = suppliers;
    purchaseOrderComponents = components;
    renderPurchaseOrders();
    $('purchase-orders-feedback').textContent = suppliers.length
      ? ''
      : 'Add a supplier using Manage suppliers before creating a purchase order.';
    $('create-purchase-order-btn').disabled =
      !['ADMIN', 'MANAGER'].includes(role) ||
      suppliers.length === 0 ||
      components.length === 0;
  } catch (error) {
    $('purchase-orders-feedback').textContent =
      `Unable to load purchase orders: ${error.message}`;
    $('purchase-orders-list').innerHTML =
      '<p class="empty-state">Purchase orders could not be loaded.</p>';
  } finally {
    refreshButton.disabled = false;
  }
}

function renderPurchaseOrders() {
  const list = $('purchase-orders-list');
  const suppliersById = new Map(
    purchaseOrderSuppliers.map(supplier => [supplier.id, supplier.name])
  );
  const componentsById = new Map(
    purchaseOrderComponents.map(component => [component.id, component])
  );

  if (!purchaseOrders.length) {
    list.innerHTML = '<p class="empty-state">No purchase orders yet.</p>';
    return;
  }

  list.innerHTML = purchaseOrders.map(order => {
    const supplierName =
      suppliersById.get(order.supplier_id) || `Supplier #${order.supplier_id}`;
    const orderDate = new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium'
    }).format(new Date(order.order_date));
    const orderItems = order.items.map(item => {
      const component = componentsById.get(item.component_id);
      const componentName = component
        ? `${component.name} (${component.sku})`
        : `Component #${item.component_id}`;
      const remaining = item.ordered_quantity - item.received_quantity;

      return `
        <li class="purchase-order-item">
          <span>${escapeHTML(componentName)}</span>
          <span>${item.received_quantity} / ${item.ordered_quantity} received</span>
          ${remaining > 0
            ? `<span class="purchase-order-outstanding">${remaining} outstanding</span>`
            : '<span class="purchase-order-complete">Complete</span>'}
        </li>
      `;
    }).join('');
    const canManage = ['ADMIN', 'MANAGER'].includes(role);
    const statusActions = canManage && order.status === 'DRAFT'
      ? `
        <button class="purchase-order-action" type="button" data-action="status" data-status="ORDERED" data-order-id="${order.id}">Mark ordered</button>
        <button class="secondary-button purchase-order-action" type="button" data-action="status" data-status="CANCELLED" data-order-id="${order.id}">Cancel order</button>
      `
      : '';
    const canReceive = canManage &&
      ['ORDERED', 'PARTIALLY_RECEIVED'].includes(order.status);
    const receiveForm = canReceive
      ? `
        <form class="purchase-order-receive-form" data-receive-order="${order.id}">
          <h4>Receive delivery</h4>
          <p>Enter the quantities delivered now. Leave other items at zero.</p>
          ${order.items.map(item => {
            const component = componentsById.get(item.component_id);
            const componentName = component
              ? `${component.name} (${component.sku})`
              : `Component #${item.component_id}`;
            const remaining = item.ordered_quantity - item.received_quantity;
            return remaining > 0
              ? `
                <label class="purchase-order-receive-item">
                  <span>${escapeHTML(componentName)} <small>(${remaining} remaining)</small></span>
                  <input
                    type="number"
                    min="0"
                    max="${remaining}"
                    step="1"
                    value="0"
                    data-order-item-id="${item.id}"
                    aria-label="Quantity received for ${escapeHTML(componentName)}"
                  >
                </label>
              `
              : '';
          }).join('')}
          <p class="purchase-order-inline-error" role="alert"></p>
          <button type="submit">Record received stock</button>
        </form>
      `
      : '';

    return `
      <article class="purchase-order-card">
        <div class="purchase-order-card-heading">
          <div>
            <p class="eyebrow">${escapeHTML(order.order_number)}</p>
            <h3>${escapeHTML(supplierName)}</h3>
            <p class="purchase-order-date">Created ${escapeHTML(orderDate)}</p>
          </div>
          <span class="purchase-order-status status-${order.status.toLowerCase().replaceAll('_', '-')}">
            ${escapeHTML(order.status.replaceAll('_', ' '))}
          </span>
        </div>
        <ul class="purchase-order-item-list">${orderItems}</ul>
        <div class="purchase-order-card-actions">
          <button class="secondary-button purchase-order-action" type="button" data-action="history" data-order-id="${order.id}">
            Receipt history
          </button>
          ${statusActions}
        </div>
        <div class="purchase-order-receipt-history" data-receipt-panel="${order.id}" hidden></div>
        ${receiveForm}
      </article>
    `;
  }).join('');
}

function appendPurchaseOrderItem() {
  const row = document.createElement('div');
  row.className = 'purchase-order-item-row';

  const label = document.createElement('label');
  label.textContent = 'Component';
  const componentSelect = document.createElement('select');
  componentSelect.name = 'component_id';
  componentSelect.required = true;
  componentSelect.innerHTML = [
    '<option value="">Choose a component</option>',
    ...purchaseOrderComponents.map(component =>
      `<option value="${component.id}">${escapeHTML(component.name)} · ${escapeHTML(component.sku)} · ${component.quantity} in stock</option>`
    )
  ].join('');
  label.append(componentSelect);

  const quantityLabel = document.createElement('label');
  quantityLabel.textContent = 'Quantity';
  const quantityInput = document.createElement('input');
  quantityInput.name = 'ordered_quantity';
  quantityInput.type = 'number';
  quantityInput.min = '1';
  quantityInput.step = '1';
  quantityInput.required = true;
  quantityInput.placeholder = 'Units';
  quantityLabel.append(quantityInput);

  const removeButton = document.createElement('button');
  removeButton.className = 'secondary-button remove-purchase-order-item';
  removeButton.type = 'button';
  removeButton.textContent = 'Remove';
  removeButton.setAttribute('aria-label', 'Remove component from order');

  row.append(label, quantityLabel, removeButton);
  $('purchase-order-items').append(row);
  updatePurchaseOrderItemRows();
}

function updatePurchaseOrderItemRows() {
  const rows = [...$('purchase-order-items').children];
  rows.forEach(row => {
    row.querySelector('.remove-purchase-order-item').disabled = rows.length === 1;
  });
}

function openPurchaseOrderDialog() {
  const supplierSelect = $('purchase-order-supplier');
  supplierSelect.innerHTML = [
    '<option value="">Choose a supplier</option>',
    ...purchaseOrderSuppliers.map(supplier =>
      `<option value="${supplier.id}">${escapeHTML(supplier.name)}</option>`
    )
  ].join('');
  $('purchase-order-supplier-help').textContent =
    purchaseOrderSuppliers.length
      ? ''
      : 'Add a supplier using Manage suppliers before creating an order.';
  $('purchase-order-items').replaceChildren();
  $('purchase-order-form-error').textContent = '';
  appendPurchaseOrderItem();
  $('purchase-order-dialog').showModal();
  supplierSelect.focus();
}

$('purchase-orders-btn').onclick = openPurchaseOrders;
$('refresh-purchase-orders').onclick = loadPurchaseOrders;
$('close-purchase-orders').onclick = closePurchaseOrders;
$('create-purchase-order-btn').onclick = openPurchaseOrderDialog;
$('close-purchase-order-dialog').onclick = () => $('purchase-order-dialog').close();
$('cancel-purchase-order').onclick = () => $('purchase-order-dialog').close();
$('add-purchase-order-item').onclick = appendPurchaseOrderItem;

$('purchase-order-items').addEventListener('click', event => {
  const removeButton = event.target.closest('.remove-purchase-order-item');
  if (removeButton && $('purchase-order-items').children.length > 1) {
    removeButton.closest('.purchase-order-item-row').remove();
    updatePurchaseOrderItemRows();
  }
});

$('purchase-order-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.target;
  const submitButton = $('submit-purchase-order');
  const formError = $('purchase-order-form-error');
  formError.textContent = '';

  const rows = [...$('purchase-order-items').querySelectorAll('.purchase-order-item-row')];
  const items = rows.map(row => ({
    component_id: Number(row.querySelector('[name="component_id"]').value),
    ordered_quantity: Number(row.querySelector('[name="ordered_quantity"]').value)
  }));
  const componentIds = items.map(item => item.component_id);

  if (componentIds.some(id => !id) || items.some(item =>
    !Number.isInteger(item.ordered_quantity) || item.ordered_quantity < 1
  )) {
    formError.textContent = 'Choose a component and enter a positive whole-number quantity for every row.';
    return;
  }

  if (new Set(componentIds).size !== componentIds.length) {
    formError.textContent = 'Each component can only be added once to an order.';
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = 'Creating...';

  try {
    const order = await api('/api/purchase-orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        supplier_id: Number($('purchase-order-supplier').value),
        items
      })
    });
    form.reset();
    $('purchase-order-dialog').close();
    await loadPurchaseOrders();
    $('purchase-orders-feedback').textContent =
      `${order.order_number} was created as a draft.`;
  } catch (error) {
    formError.textContent = error.message;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Create order';
  }
});

$('purchase-orders-list').addEventListener('click', async event => {
  const actionButton = event.target.closest('[data-action]');
  if (!actionButton) return;

  const orderId = actionButton.dataset.orderId;
  if (actionButton.dataset.action === 'history') {
    const panel = $('purchase-orders-list').querySelector(
      `[data-receipt-panel="${orderId}"]`
    );
    if (!panel.hidden) {
      panel.hidden = true;
      return;
    }

    actionButton.disabled = true;
    panel.hidden = false;
    panel.textContent = 'Loading receipt history...';
    try {
      const receipts = await api(`/api/purchase-orders/${orderId}/receipts`);
      const order = purchaseOrders.find(item => String(item.id) === orderId);
      const orderItems = new Map(
        (order ? order.items : []).map(item => [item.id, item.component_id])
      );
      const components = new Map(
        purchaseOrderComponents.map(component => [component.id, component.name])
      );
      panel.innerHTML = receipts.length
        ? `<h4>Receipt history</h4><ul>${receipts.map(receipt => {
          const componentId = orderItems.get(receipt.purchase_order_item_id);
          const componentName = components.get(componentId) || `Component #${componentId}`;
          const receivedAt = new Intl.DateTimeFormat(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short'
          }).format(new Date(receipt.received_at));
          return `<li>${escapeHTML(componentName)}: ${receipt.received_quantity} received on ${escapeHTML(receivedAt)}</li>`;
        }).join('')}</ul>`
        : '<p>No stock has been received yet.</p>';
    } catch (error) {
      panel.textContent = `Unable to load receipt history: ${error.message}`;
    } finally {
      actionButton.disabled = false;
    }
    return;
  }

  if (actionButton.dataset.action === 'status') {
    const status = actionButton.dataset.status;
    if (
      status === 'CANCELLED' &&
      !window.confirm('Cancel this purchase order? This cannot be undone.')
    ) {
      return;
    }

    actionButton.disabled = true;
    try {
      await api(`/api/purchase-orders/${orderId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      await loadPurchaseOrders();
      $('purchase-orders-feedback').textContent =
        `Purchase order status updated to ${status.toLowerCase()}.`;
    } catch (error) {
      $('purchase-orders-feedback').textContent =
        `Unable to update purchase order: ${error.message}`;
      actionButton.disabled = false;
    }
  }
});

$('purchase-orders-list').addEventListener('submit', async event => {
  const form = event.target.closest('[data-receive-order]');
  if (!form) return;
  event.preventDefault();

  const errorElement = form.querySelector('.purchase-order-inline-error');
  const submitButton = form.querySelector('[type="submit"]');
  errorElement.textContent = '';
  const items = [...form.querySelectorAll('[data-order-item-id]')]
    .map(input => ({
      purchase_order_item_id: Number(input.dataset.orderItemId),
      received_quantity: Number(input.value)
    }))
    .filter(item => item.received_quantity > 0);

  if (!items.length) {
    errorElement.textContent = 'Enter at least one quantity to receive.';
    return;
  }
  if (items.some(item => !Number.isInteger(item.received_quantity))) {
    errorElement.textContent = 'Received quantities must be whole numbers.';
    return;
  }

  if (!form.dataset.idempotencyKey) {
    form.dataset.idempotencyKey =
      globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function'
        ? globalThis.crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  submitButton.disabled = true;
  submitButton.textContent = 'Recording...';
  try {
    await api(`/api/purchase-orders/${form.dataset.receiveOrder}/receive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idempotency_key: form.dataset.idempotencyKey,
        items
      })
    });
    await Promise.all([loadPurchaseOrders(), refresh()]);
    $('purchase-orders-feedback').textContent =
      'Delivery recorded and inventory updated.';
  } catch (error) {
    errorElement.textContent = error.message;
    await loadPurchaseOrders();
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Record received stock';
  }
});

// ==================== HTML ESCAPING =============
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



// ==================== INITIALIZE APPLICATION =============
setLoggedIn();