import test from 'node:test';
import assert from 'node:assert/strict';
import { scriptStatusInfo, scriptProgress, scriptsNeedingAttention } from './scriptStatus.js';

test('maps every backend analysis_status to a label and tone', () => {
  assert.deepEqual(scriptStatusInfo('complete'), { label: 'Analysis complete', tone: 'good' });
  assert.deepEqual(scriptStatusInfo('analyzing'), { label: 'Analysing', tone: 'info' });
  assert.deepEqual(scriptStatusInfo('analysis_queued'), { label: 'Analysing', tone: 'info' });
  assert.deepEqual(scriptStatusInfo('failed'), { label: 'Analysis failed', tone: 'bad' });
  assert.deepEqual(scriptStatusInfo('error'), { label: 'Analysis failed', tone: 'bad' });
  assert.deepEqual(scriptStatusInfo('cancelled'), { label: 'Analysis cancelled', tone: 'warn' });
  assert.deepEqual(scriptStatusInfo('pending'), { label: 'Not analysed yet', tone: 'neutral' });
  assert.deepEqual(scriptStatusInfo('ready_for_analysis'), { label: 'Not analysed yet', tone: 'neutral' });
});

test('missing or unknown status is neutral and never throws', () => {
  assert.equal(scriptStatusInfo(undefined).tone, 'neutral');
  assert.equal(scriptStatusInfo('something_new').tone, 'neutral');
});

test('script-level in_progress counts as analysing', () => {
  assert.deepEqual(scriptStatusInfo('in_progress'), { label: 'Analysing', tone: 'info' });
});

const counts = (scene_count, analyzed_scenes, extra = {}) => ({
  scene_count, analyzed_scenes, analyzing_scenes: 0, failed_scenes: 0, ...extra,
});

test('progress is derived from scene counts, ignoring the unmaintained script status', () => {
  // The real bug: script-level status is always "pending" even when fully analysed.
  assert.deepEqual(scriptProgress({ analysis_status: 'pending', ...counts(80, 80) }),
    { label: 'Analysis complete', tone: 'good' });
  assert.deepEqual(scriptProgress({ analysis_status: 'pending', ...counts(80, 30) }),
    { label: '30/80 scenes analysed', tone: 'warn' });
  assert.deepEqual(scriptProgress({ analysis_status: 'pending', ...counts(80, 0) }),
    { label: 'Not analysed yet', tone: 'neutral' });
  assert.deepEqual(scriptProgress({ ...counts(0, 0) }), { label: 'Not analysed yet', tone: 'neutral' });
});

test('scenes being analysed or failed take priority', () => {
  assert.deepEqual(scriptProgress(counts(80, 30, { analyzing_scenes: 4 })),
    { label: 'Analysing 30/80', tone: 'info' });
  assert.deepEqual(scriptProgress(counts(80, 30, { failed_scenes: 1 })),
    { label: '1 scene failed', tone: 'bad' });
  assert.deepEqual(scriptProgress(counts(80, 30, { failed_scenes: 3, analyzing_scenes: 2 })),
    { label: '3 scenes failed', tone: 'bad' });
});

test('older payloads without counts fall back to the script-level status', () => {
  assert.deepEqual(scriptProgress({ analysis_status: 'failed' }), { label: 'Analysis failed', tone: 'bad' });
  assert.equal(scriptProgress({}).tone, 'neutral');
});

test('attention list holds scripts that are analysing, failed or partly analysed', () => {
  const scripts = [
    { id: 'a', ...counts(10, 10) },
    { id: 'b', ...counts(10, 4, { analyzing_scenes: 2 }) },
    { id: 'c', ...counts(10, 0) },
    { id: 'd', ...counts(10, 9, { failed_scenes: 1 }) },
    { id: 'e', ...counts(10, 5) },
  ];
  assert.deepEqual(scriptsNeedingAttention(scripts).map((x) => x.id), ['b', 'd', 'e']);
  assert.deepEqual(scriptsNeedingAttention([]), []);
});
