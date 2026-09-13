# Phase 2 Roadmap (Backlog — Not Scheduled for MVP)

This is a backlog, not an implementation plan — do not start these until sub-plans 1–8 are complete and the studio has piloted the MVP. Each item should get its own `docs/plan/1X-*.md` implementation plan, written with `superpowers:writing-plans`, when it's actually scheduled.

## Candidate items (from the original brief §6)

1. **Loudness normalization (LUFS target) on export**
   Likely implementation: `ffmpeg-normalize` or FFmpeg's own `loudnorm` filter, added as an optional post-conversion step in `converter.py`. Needs a new `ConversionOptions.target_lufs: float | None` field.

2. **Silence trimming at start/end**
   FFmpeg's `silenceremove` filter, also a `converter.py` option.

3. **"Send to DAW" watch-folder integration**
   Simplest version: a Settings option to also copy (not move) completed files into a second folder the user's DAW watches. No DAW-specific API integration needed for v1 of this feature.

4. **Waveform preview before download**
   Would need to download a short preview clip or decode the full raw stream client-side (e.g., via `pydub`/`numpy` + a `QPainter`-based waveform widget). Non-trivial; scope carefully before committing.

5. **Auto-update mechanism for the app itself**
   Options: a simple "check GitHub releases" HTTP call + prompt-to-download, or a full updater framework. Evaluate cost/benefit given the app is likely distributed to one studio, not the public.

6. **Auto-update for yt-dlp**
   Partially covered by sub-plan 3 Task 3 (`update_ytdlp()`) — Phase 2 would add a startup check that nudges the user when their yt-dlp is more than N days old, rather than requiring a manual click.

7. **Stem separation (vocal/instrumental split)**
   Stretch feature. Would integrate an open-source model (e.g., Demucs) as an optional heavyweight dependency — likely a separate optional install, not bundled into the base installer, given model size and GPU/CPU inference time.

## Not in scope for Phase 2 either (explicitly out of scope per the brief)

- Redistribution/sharing features of any kind (legal risk — see disclaimer in sub-plan 6).
- macOS/Linux builds, unless the studio's hardware changes.
- Telemetry/analytics of any kind.
