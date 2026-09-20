const assert = require('node:assert/strict');
const {test} = require('node:test');
const catalog = require('./conferences.json');
const {ordinal, lookupConference} = require('./conference-lookup.js');

test('verified editions override a mistaken saved edition', () => {
  const wrong = [{conference: 'EC', year: '2026', citation: '26th ACM Conference on Economics and Computation'}];
  assert.equal(lookupConference('EC', '2026', catalog, wrong).citation, '27th ACM Conference on Economics and Computation');
});

test('infers forwards and backwards with correct ordinal suffixes', () => {
  assert.equal(lookupConference('EC', '2027', catalog).citation, '28th ACM Conference on Economics and Computation');
  assert.equal(lookupConference('EC', '2025', catalog).citation, '26th ACM Conference on Economics and Computation');
  assert.equal(lookupConference('WINE', '2025', catalog).targetEdition, 21);
  assert.equal(lookupConference('SAGT', '2019', catalog).targetEdition, 12);
  assert.equal(lookupConference('WWW', '2024', catalog).targetEdition, 33);
  assert.deepEqual([1, 2, 3, 11, 12, 13, 21, 22, 23, 111, 112, 113].map(ordinal),
    ['1st', '2nd', '3rd', '11th', '12th', '13th', '21st', '22nd', '23rd', '111th', '112th', '113th']);
});

test('case, whitespace, full names, and aliases resolve to the same conference', () => {
  for (const venue of ['neurips', ' NeurIPS ', 'NIPS', 'Conference on Neural Information Processing Systems']) {
    assert.equal(lookupConference(venue, '2027', catalog).targetEdition, 41);
  }
});

test('a saved publication provides a baseline for a new conference', () => {
  const saved = [{conference: 'NEW', year: '2024', citation: '11th Example Conference'}];
  const result = lookupConference('new', '2026', catalog, saved);
  assert.equal(result.citation, '13th Example Conference');
  assert.equal(result.origin, 'publication');
  assert.equal(result.inferred, true);
});

test('unknown venues, invalid years, and impossible editions are not fabricated', () => {
  assert.equal(lookupConference('Unknown', '2026', catalog), null);
  assert.equal(lookupConference('EC', '', catalog), null);
  assert.equal(lookupConference('EC', '202', catalog), null);
  assert.ok(lookupConference('EAAMO', '2020', catalog).error);
});

test('conflicting unverified baselines require a manual correction', () => {
  const saved = [{conference: 'NEW', year: '2024', citation: '11th Example Conference'},
    {conference: 'NEW', year: '2025', citation: '11th Example Conference'}];
  assert.ok(lookupConference('NEW', '2026', catalog, saved).error);
});

test('each verified reference returns its checked baseline and source', () => {
  for (const [venue, baseline] of Object.entries(catalog)) {
    const result = lookupConference(venue, String(baseline.year), catalog);
    assert.equal(result.targetEdition, baseline.edition);
    assert.equal(result.inferred, false);
    assert.equal(result.source, baseline.source);
    assert.ok(result.source.startsWith('https://'));
  }
});
