const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require('node:path').join(__dirname, '../frontend/config.js'), 'utf8');
test('links and persisted overrides cannot redirect private uploads', () => {
  let removed;
  const window = { location: { origin: 'https://clinic.example', search: '?api=https://attacker.example' },
    localStorage: { getItem: () => 'https://attacker.example', removeItem: key => {removed = key;} } };
  vm.runInNewContext(source, {window, URL});
  assert.equal(window.MEDICTIME_CONFIG.API_BASE_URL, 'https://clinic.example');
  assert.equal(removed, 'medictime.apiBaseUrl');
  assert.ok(Object.isFrozen(window.MEDICTIME_CONFIG));
});
test('remote plaintext HTTP is rejected', () => {
  const window = {location: {origin: 'http://remote.example'}, localStorage: {removeItem() {}}};
  assert.throws(() => vm.runInNewContext(source, {window, URL}), /HTTPS/);
});
