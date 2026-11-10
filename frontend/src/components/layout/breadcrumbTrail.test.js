import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTrail } from './breadcrumbTrail.js';

const prod = { id: 'p1', title: 'Looped Feature' };
const script = { id: 's1', title: 'Pilot' };
const c = (label, to = null) => ({ label, to });

test('root pages have no breadcrumb', () => {
  for (const pathname of ['/', '/scripts', '/productions', '/contacts', '/locations', '/series']) {
    assert.deepEqual(buildTrail({ pathname }), [], pathname);
  }
});

test('unknown routes have no breadcrumb', () => {
  assert.deepEqual(buildTrail({ pathname: '/nope/xyz' }), []);
});

test('production overview', () => {
  const want = [c('Productions', '/productions'), c('Looped Feature')];
  assert.deepEqual(buildTrail({ pathname: '/productions/p1', production: prod }), want);
  assert.deepEqual(buildTrail({ pathname: '/productions/p1/overview', production: prod }), want);
});

test('production tab adds the tab label', () => {
  assert.deepEqual(buildTrail({ pathname: '/productions/p1/crew', production: prod }), [
    c('Productions', '/productions'), c('Looped Feature', '/productions/p1'), c('Crew'),
  ]);
  assert.equal(buildTrail({ pathname: '/productions/p1/callsheet', production: prod }).at(-1).label, 'Call Sheet');
});

test('unknown production tab is treated as overview', () => {
  assert.deepEqual(buildTrail({ pathname: '/productions/p1/bogus', production: prod }), [
    c('Productions', '/productions'), c('Looped Feature'),
  ]);
});

test('production title still loading falls back to a placeholder label', () => {
  assert.equal(buildTrail({ pathname: '/productions/p1' }).at(-1).label, 'Production');
});

test('scene breakdown under a production', () => {
  assert.deepEqual(buildTrail({ pathname: '/scenes/s1', script, production: prod }), [
    c('Productions', '/productions'), c('Looped Feature', '/productions/p1'), c('Pilot'),
  ]);
});

test('scene breakdown without a production', () => {
  assert.deepEqual(buildTrail({ pathname: '/scenes/s1', script }), [c('Scripts', '/scripts'), c('Pilot')]);
});

test('script section under a production', () => {
  assert.deepEqual(buildTrail({ pathname: '/scripts/s1/stripboard', script, production: prod }), [
    c('Productions', '/productions'), c('Looped Feature', '/productions/p1'),
    c('Pilot', '/scenes/s1'), c('Stripboard'),
  ]);
});

test('manage section is labelled Revisions', () => {
  assert.equal(buildTrail({ pathname: '/scripts/s1/manage', script }).at(-1).label, 'Revisions');
});

test('script not loaded yet gets a neutral label, never undefined', () => {
  assert.equal(buildTrail({ pathname: '/scenes/s1', script: null }).at(-1).label, 'Script');
});

test('upload, profile, billing', () => {
  assert.deepEqual(buildTrail({ pathname: '/upload' }), [c('Scripts', '/scripts'), c('Upload Script')]);
  assert.deepEqual(buildTrail({ pathname: '/profile' }), [c('Profile')]);
  assert.deepEqual(buildTrail({ pathname: '/billing' }), [c('Billing')]);
});

test('series and season detail', () => {
  assert.deepEqual(buildTrail({ pathname: '/series/x' }), [c('Scripts', '/scripts'), c('Series', '/series'), c('Series')]);
  assert.deepEqual(buildTrail({ pathname: '/series/x/seasons/y' }), [
    c('Scripts', '/scripts'), c('Series', '/series'), c('Series', '/series/x'), c('Season'),
  ]);
});

test('contact and location detail', () => {
  assert.deepEqual(buildTrail({ pathname: '/contacts/abc' }), [c('Contacts', '/contacts'), c('Contact')]);
  assert.deepEqual(buildTrail({ pathname: '/locations/abc/edit' }), [c('Locations', '/locations'), c('Location')]);
});

test('production cast list', () => {
  assert.deepEqual(buildTrail({ pathname: '/productions/p1/cast', production: prod }), [
    c('Productions', '/productions'), c('Looped Feature', '/productions/p1'), c('Cast'),
  ]);
});

test('production cast for one script links back to the cast list', () => {
  assert.deepEqual(buildTrail({ pathname: '/productions/p1/cast/s1', production: prod, script }), [
    c('Productions', '/productions'), c('Looped Feature', '/productions/p1'),
    c('Cast', '/productions/p1/cast'), c('Pilot'),
  ]);
});
