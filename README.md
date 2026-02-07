# keep_or_discard
Organize photos locally. This app lets you quickly review every image in `./media`, tag each as keep or discard, and then copy or move the selected files (and any matching RAW originals) into tidy `keep/` and `discard/` folders.

## Safe workflow (recommended)
1. Put images in `./media`.
2. Review and tag.
3. Use **Copy to keep/discard** first.
4. Verify `keep/` and `discard/`.
5. Optionally use **Cleanup originals** to move originals to `discard/_originals`.

## Folders
- `media/`: source images (you add files here)
- `keep/`: kept images and RAWs
- `discard/`: discarded images and RAWs
- `.keep_or_discard/`: session state and exports

Quick shortcuts: `←/A` discard, `→/D/Space` keep, `U/Z` undo. Sessions autosave locally in `.keep_or_discard/session_state.json`.
