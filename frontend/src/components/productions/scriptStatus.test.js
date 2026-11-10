import test from 'node:test';
import assert from 'node:assert/strict';
import { scriptStatusInfo, scriptsNeedingAttention } from './scriptStatus.js';

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

test('attention list holds only analysing and failed scripts, in input order', () => {
  const scripts = [
    { id: 'a', analysis_status: 'complete' },
    { id: 'b', analysis_status: 'analyzing' },
    { id: 'c', analysis_status: 'pending' },
    { id: 'd', analysis_status: 'failed' },
    { id: 'e' },
  ];
  assert.deepEqual(scriptsNeedingAttention(scripts).map((s) => s.id), ['b', 'd']);
  assert.deepEqual(scriptsNeedingAttention([]), []);
});
