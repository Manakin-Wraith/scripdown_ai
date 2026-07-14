import assert from 'node:assert/strict';
import { buildScheduledMap } from '../src/utils/scheduleMap.mjs';

// scenes assigned across two days
const days = [
  { id: 'd1', day_number: 1, scenes: [{ scene_id: 's1' }, { scene_id: 's2' }] },
  { id: 'd2', day_number: 2, scenes: [{ scene_id: 's3' }] },
];
const map = buildScheduledMap(days);
assert.equal(map.size, 3);
assert.deepEqual(map.get('s1'), { dayNumber: 1 });
assert.deepEqual(map.get('s3'), { dayNumber: 2 });
assert.equal(map.has('s4'), false);

// tolerates missing/empty input
assert.equal(buildScheduledMap(undefined).size, 0);
assert.equal(buildScheduledMap([]).size, 0);
assert.equal(buildScheduledMap([{ day_number: 5 }]).size, 0); // day with no scenes

// skips malformed scene rows
const map2 = buildScheduledMap([{ day_number: 1, scenes: [{ scene_id: 's1' }, {}, null] }]);
assert.equal(map2.size, 1);
assert.deepEqual(map2.get('s1'), { dayNumber: 1 });

console.log('OK: buildScheduledMap');
