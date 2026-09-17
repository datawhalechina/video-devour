/** One writer per document: coalesce edits, advance revisions only after acknowledgement. */
export function createAutosave({ save, revision, notify, persist, clear, delay = 700 }) {
  let pending, active = false, timer, stopped = false, conflict = false, conflictMessage = '';
  const schedule = (wait = delay) => { clearTimeout(timer); timer = setTimeout(flush, wait); };
  async function flush() {
    clearTimeout(timer); timer = undefined;
    if (active || !pending || conflict) return;
    active = true;
    const snapshot = pending; pending = undefined;
    let succeeded = false;
    notify('saving');
    try {
      const result = await save({ ...snapshot, expected_revision: revision, schema_version: 1 });
      revision = result.revision; succeeded = true;
      if (pending) persist(pending, revision);
      else { clear(); notify('saved'); }
    } catch (error) {
      pending ||= snapshot;
      persist(pending, revision);
      conflict = error.status === 409;
      if (conflict) conflictMessage = error.message;
      notify(conflict ? 'conflict' : 'error', error.message);
      if (!conflict && !stopped) schedule(3000);
    } finally {
      active = false;
      if (pending && !conflict && !timer) {
        if (!stopped) schedule();
        else if (succeeded) void flush();
      }
    }
  }
  return {
    change(snapshot) { pending = snapshot; persist(snapshot, revision); notify(conflict ? 'conflict' : 'pending', conflictMessage); if (!conflict) schedule(); },
    flush,
    dirty: () => active || !!pending,
    stop() { stopped = true; clearTimeout(timer); timer = undefined; void flush(); },
  };
}
