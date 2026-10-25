
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const appPath = path.join(__dirname, '..', 'app.js');
const appSource = fs.readFileSync(appPath, 'utf8');

// Extract the actual escapeHTML function from the application.
const start = appSource.indexOf('function escapeHTML(value) {');

assert.notEqual(
  start,
  -1,
  'escapeHTML() must exist in frontend/app.js'
);

const functionBodyStart = start;
const nextSection = appSource.indexOf(
  '// ==================== DELETE COMPONENT ====================',
  functionBodyStart
);

assert.notEqual(
  nextSection,
  -1,
  'Could not locate the section following escapeHTML()'
);

const functionSource = appSource.slice(functionBodyStart, nextSection);

const context = {};
vm.createContext(context);
vm.runInContext(functionSource, context);

const escapeHTML = context.escapeHTML;

test('escapes script tags', () => {
  assert.equal(
    escapeHTML('<script>alert(1)</script>'),
    '&lt;script&gt;alert(1)&lt;/script&gt;'
  );
});

test('escapes HTML event-handler payloads', () => {
  assert.equal(
    escapeHTML('<img src=x onerror=alert(1)>'),
    '&lt;img src=x onerror=alert(1)&gt;'
  );
});

test('escapes quotes and ampersands', () => {
  assert.equal(
    escapeHTML(`'"><&`),
    '&#39;&quot;&gt;&lt;&amp;'
  );
});

test('converts null and undefined to empty strings', () => {
  assert.equal(escapeHTML(null), '');
  assert.equal(escapeHTML(undefined), '');
});

test('converts ordinary text to a string', () => {
  assert.equal(escapeHTML('Keyboard'), 'Keyboard');
});

test('escapes HTML-like inventory names', () => {
  assert.equal(
    escapeHTML('<b>Inventory</b>'),
    '&lt;b&gt;Inventory&lt;/b&gt;'
  );
});
