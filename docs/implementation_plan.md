# Framework integration implementation plan

Goal: Deliver a new independently runnable repository matching the supplied five-interface room measurement framework. Keep Efficient RANSAC native supports -> geometric wall screening -> SVD -> RMS with no filtering or point recovery.

Architecture: Reuse the verified room_walls geometry core. Add room_measurement contracts and an orchestrator, replaceable opening/corner/local-region interfaces, raw-coordinate RMS with polygon masks, and Word reporting. Native support RMS remains available even when whole structural corners are not reliable. Opening candidates are not automatically treated as verified openings.

Scope: Your responsibility is full-room input to wall roughness plus explicit interface delivery. Optional door/window and structural dimension modules are geometric candidate implementations and team replacement points, not claimed fully validated semantic detectors. Official Task 1 also requires room dimensions and door/window dimensions; the image alone does not establish their metrology accuracy.

Plan:
1. Copy only current production core/native adapters, exclude old recovery and filtering experiments from new delivery. Preserve old projects.
2. Define units, up axis, source hashes, 0-based original point IDs, wall frames, opening polygons and status contracts.
3. Write failing tests for exact native membership, masks, four-corner geometry, non-Z up, local coverage and missing-data behavior.
4. Implement five interfaces and CLI with optional external annotations, plugin callbacks and machine-readable exports.
5. Implement conservative geometric opening candidates, gated structural corners, 1x1 m local regions, and optional opening exclusion without distance filtering.
6. Add executable synthetic example, install/build instructions and dependency/source provenance.
7. Run tests and complete original M04/M26 pipeline. Audit support RMS against existing values and output row IDs against original clouds. Render Word reports.
8. Write Chinese handoff documentation describing total tasks, your work, inputs/outputs, completed work, limits and teammate requirements. Render and inspect all pages.
9. Create a new public GitHub repo under x13230802751, upload clean sources/docs/test evidence only, verify remote HEAD and visibility. Do not upload course data, PDFs, local dependencies or unrelated experiment history.

Acceptance: Five callable interfaces with a runnable whole-room coordinator; exact raw index provenance; no 50 mm band or denoising; missing closure yields needs_review instead of fake structural corners; accurate documentation and real execution evidence; fresh repository link.
