# Editable mind maps

`tree.js` owns immutable tree operations and visible layout. `MindmapEditor` owns selection,
undo/redo, outline, and automatic persistence; `TreeCanvas` handles geometry and pointer gestures.
Knowledge graphs remain separate because they are not trees.

The server stores `mindmap.document.json` beside the report, addressed by task and pinned run.
Generated HTML is an import source only. Explicit import is undoable; loading AI output does not
overwrite user edits. PUT requires the last revision, returns 409 on concurrent edits, writes
atomically, and retains the last 20 previous snapshots. Browser drafts survive failed saves.
Undo/redo retains 50 edits during the current session; historical snapshot restoration has no UI.

Double-click or F2 edits a title inline. Tab adds a child, Enter adds a sibling. Drop in a node's
center to reparent, or in its top quarter to insert before it. Root deletion and cyclic moves are
rejected. Fold state and notes are persisted. SVG export includes currently visible branches.

Validation:

```sh
node --test frontend/src/features/mindmap/tree.test.js
.venv/bin/python -m unittest discover -s tests -p test_mindmap.py -v
```

Use the isolated fixture server's `/learn/fixture-04-1/mindmap` for interaction checks.
