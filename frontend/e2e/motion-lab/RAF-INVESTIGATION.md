# Video suite: RAF lifecycle investigation

The failure was reproduced with test-only requestAnimationFrame stack tracking.
After destroy and the former 250ms delay, the pending callback was `_rafBugFix`:
`instrument.js:8 → node_modules/gsap/ScrollTrigger.js:62`. The other live owner
before destroy was GSAP's `_tick` (`gsap-core.js:1304`).

ScrollTrigger's `_rafBugFix` schedules itself only while `_enabled` is true.
`ScrollTrigger.disable()` makes that condition false, without retaining/cancelling
the frame already queued by this helper. Its next execution terminates the chain.
Wall-clock elapsed time does not prove that a browser frame has executed.

The test now samples immediately after destroy and after one and two actual RAF
boundaries. It still requires zero scheduled RAFs, triggers, listeners and video
frame callbacks; it does not ignore an owner or weaken the zero assertion.
The temporary stack wrapper and debug logging were removed. Runtime and GSAP
dependency sources were not changed. Samples are recorded in cleanupFrames in
the JSON report.

Metadata investigation: listeners are registered before src/load in video-seek.mjs,
and pump checks real readyState and finite duration. No missed-event race was
demonstrated. The old seek assertion spent its 6s budget on both initial loading
and seeking, although the feature's existing metadata watchdog is 10s. The test
now waits on actual readiness or feature failure before starting the existing
6s seek assertion. The runtime watchdog is unchanged; failures remain failures.
The historical parallel-run timeout does not prove local-server saturation;
no server/CPU trace exists for that run, so its precise environmental cause
remains unknown.

Preserved: visual composition, intro, hero, CTA, seeker, narrative cuts, media
assets and functional HOME. No dependency installation or asset encoding.

Three isolated final runs: 18/18 each. All three recorded exactly the same
cleanup sequence: immediately `['_rafBugFix']`, after frame1 `[]`, after frame2
`[]`. Reports: artifacts/video-validation/raf-run-1.json through raf-run-3.json.

Legacy checks.mjs: 17/17 after the three runs. Additional browser probes covered
direct #ritual entry, reload there, forward/reverse seeks, exit and destroy:
again [_rafBugFix] → [] → []. Reduced-motion destroy returned zero RAFs.
Destroy while the media request was blocked (readyState0) returned zero RAFs and
zero video-frame callbacks after two frames. Delayed metadata/latest-target
behavior is also covered by every successful video-suite run.

git diff --check reports only the preexisting AGENTS.md:29 whitespace.
