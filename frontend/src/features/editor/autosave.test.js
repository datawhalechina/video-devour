import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createAutosave } from './autosave.js';
const tick = () => new Promise(resolve => setTimeout(resolve, 15));
test('serializes in-flight edits and carries the acknowledged revision', async () => {
  let release; const calls=[]; let cleared=0;
  const saver=createAutosave({ revision:'a', delay:1, notify(){}, persist(){}, clear(){cleared++;}, save: body => {
    calls.push(body); return calls.length===1 ? new Promise(r=>{release=r;}) : Promise.resolve({revision:'c'});
  }});
  saver.change({markdown:'first'}); await tick();
  saver.change({markdown:'second'}); saver.change({markdown:'latest'}); await tick();
  assert.equal(calls.length,1); release({revision:'b'}); await tick();
  assert.equal(calls.length,2); assert.equal(calls[1].markdown,'latest'); assert.equal(calls[1].expected_revision,'b');
  assert.equal(cleared,1); assert.equal(saver.dirty(),false); saver.stop();
});
test('conflict preserves newest draft and pauses subsequent writes', async () => {
  const states=[]; let draft; let calls=0;
  const saver=createAutosave({revision:'a', delay:1,notify:s=>states.push(s),persist:s=>{draft=s;},clear(){throw Error('must retain');},save:async()=>{calls++;throw Object.assign(Error('conflict'),{status:409});}});
  saver.change({markdown:'mine'}); await tick(); saver.change({markdown:'newest'}); await tick();
  assert.equal(calls,1); assert.equal(draft.markdown,'newest'); assert.ok(states.includes('conflict')); saver.stop();
});
