import assert from 'node:assert/strict';
import { buildScheduledMap, buildShootDayBlocks } from '../src/utils/scheduleMap.mjs';

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

// Full scene objects keyed by id (insertion order preserved by Map)
const sById = new Map([
  ['s1', { id: 's1', scene_number: '1' }],
  ['s2', { id: 's2', scene_number: '2' }],
  ['s3', { id: 's3', scene_number: '3' }],
  ['s4', { id: 's4', scene_number: '4' }], // never assigned → unscheduled
]);
const blkDays = [
  { id: 'd1', day_number: 1, scenes: [{ scene_id: 's2' }, { scene_id: 's1' }] }, // note order s2,s1
  { id: 'd2', day_number: 2, scenes: [{ scene_id: 's3' }, { scene_id: 's99' }] }, // s99 stale
];
const blocks = buildShootDayBlocks(blkDays, sById);
// two day blocks + one unscheduled block
assert.equal(blocks.length, 3);
assert.equal(blocks[0].dayNumber, 1);
assert.deepEqual(blocks[0].scenes.map((s) => s.id), ['s2', 's1']); // schedule order preserved
assert.equal(blocks[1].dayNumber, 2);
assert.deepEqual(blocks[1].scenes.map((s) => s.id), ['s3']); // stale s99 skipped
assert.equal(blocks[2].unscheduled, true);
assert.deepEqual(blocks[2].scenes.map((s) => s.id), ['s4']);

// no unscheduled scenes → no unscheduled block
const sAll = new Map([['s1', { id: 's1' }]]);
const blocksNoBin = buildShootDayBlocks(
  [{ day_number: 1, scenes: [{ scene_id: 's1' }] }],
  sAll,
);
assert.equal(blocksNoBin.length, 1);
assert.equal(blocksNoBin[0].unscheduled, undefined);

// empty/undefined days → single unscheduled block with all scenes
const blocksNoDays = buildShootDayBlocks(undefined, sAll);
assert.equal(blocksNoDays.length, 1);
assert.equal(blocksNoDays[0].unscheduled, true);
assert.deepEqual(blocksNoDays[0].scenes.map((s) => s.id), ['s1']);

// empty scenesById → no blocks at all
assert.equal(buildShootDayBlocks(blkDays, new Map()).length, 0);

console.log('OK: buildShootDayBlocks');
