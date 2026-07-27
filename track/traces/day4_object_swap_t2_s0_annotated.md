# Day-4 Annotated Harness Trace — `libero_object_swap` task 2, seed 0

**Run dir:** `artifacts/harness/day4_object_swap_t2_s0_r2/` (gitignored; not committed — this file is the durable record)
**Command:** `.venv/bin/rpent --env libero --suite libero_object_swap --task 2 --seed 0 --planner claude_code --model claude-opus-4-8 --max-turns 60 --output-dir artifacts/harness/day4_object_swap_t2_s0_r2`
**Task language:** "Pick the salad dressing and place it in the basket"
**Planner:** `claude_code` backend, model `claude-opus-4-8`, Claude Agent SDK, timeout 1200 s, advisory budget $10.0
**Outcome:** SUCCESS — `libero_terminated: true` (verified in `states.json` step_idx 13, see Audit 4) — in 437.0 s (agent-reported), 439.8 s (harness-reported wall time)

This file annotates every `[tool->]`/`[tool<-]` pair from `run.log` (identical content also appears in `claude_object_swap_t2_s0.txt`) against the paper's harness mechanisms: **memory read**, **semantic grounding**, **localization**, **staging**, **bounded VLA invocation**, **verification**, **retry**, **staged transport**, **recipe write**, and **terminal predicate**.

Three mechanism highlights are called out inline with `>>> HIGHLIGHT` markers:
1. **Re-grounding vs. stored literals** (turns 7–9)
2. **Failed-release retry loop** (turns 15–20)
3. **Empty-grasp recovery with analytic fallback** (turns 20–26)

---

## Turn-by-turn trace

### Turn 1 — 00:42:10
| | |
|---|---|
| Tool calls | `read_text_file {"path":"resources/libero/memory/MEMORY.md"}` (13851 B), `view_driver_state {"step":0}` (1619 B) |
| Purpose | Load the memory index and the initial driver/env state |
| Outcome | Both reads succeed |
| Mechanism | **memory read** (index) + **verification** (initial state snapshot) |

### Turn 2 — 00:42:15
| | |
|---|---|
| Tool calls | `read_text_file` x3: `tall_item_first_basket_placement.md` (9336 B), `feedback_staged_held_object_transport.md` (2367 B), `feedback_pi0_pick_full_prompt.md` (1850 B); `list_dir {"path":"resources/libero/results_object_pert"}` (1646 B); `read_text_file` on `images_cam_hi/image_cam_hi_00.png` — **error** (149 B, `is_error:true`, wrong tool for a binary PNG) |
| Purpose | Pull the three memory leaves relevant to a tall-bottle/basket task (staging pattern, held-object-transport pattern, pi0 prompt-phrasing pattern) and list prior seed-0 reference artifacts |
| Outcome | Memory reads succeed; the image read via the text-file tool fails as expected (PNG via `read_text_file`) |
| Mechanism | **memory read** (situational feedback files) — note the planner reasoned explicitly: "a low-table grocery scene (EEF z≈0.26)" before pulling these, i.e. hypothesis-driven memory retrieval, not blind index traversal |

### Turn 3 — 00:42:21
| | |
|---|---|
| Tool calls | `read_text_file` on `results_object_pert/object_swap_t2_s0.json` (3145 B, the reference audit) and `recipe_object_swap_t2_s0.jsonl` (792 B, the reference recipe skeleton); `Read` (Claude Code native tool, wrong path `RPent/artifacts/...`) — **error** |
| Purpose | Read the seed-0 reference audit/recipe as a *technique* prior (per the hybrid guide's explicit instruction: templates only, never coordinate sources) |
| Outcome | Reference docs loaded; image path attempt fails (path typo including a stray `RPent/` segment) |
| Mechanism | **memory read** (reference-scene technique prior) |

### Turn 4 — 00:42:32
| | |
|---|---|
| Tool calls | `list_dir` on `images_cam_hi` — **error** (134 B); `list_dir` on the run root — **error** (120 B) |
| Purpose | Recover from the path-resolution failure by listing the actual output directory |
| Outcome | Both list attempts still fail (relative-path resolution issue inside the sandboxed tool) |
| Mechanism | **retry** (path-recovery, pre-perception) |

### Turn 5 — 00:42:37
| | |
|---|---|
| Tool call | `Bash {"command":"find / -type d -name day4_object_swap_t2_s0_r2 ...; ls -d artifacts/harness/*t2_s0*"}` — **error** (92 B) |
| Purpose | Use the native shell tool to locate the true absolute path to the run's artifact tree |
| Outcome | Still errors, but this and the prior two turns converge the planner onto the correct absolute path used from turn 6 onward |
| Mechanism | **retry** (infra path-recovery) |

### Turn 6 — 00:43:02
| | |
|---|---|
| Tool call | `Read {"file_path":"/home/demo/github_sow_harnessVLA/artifacts/harness/day4_object_swap_t2_s0_r2/images_cam_hi/image_cam_hi_00.png"}` |
| Purpose | Load the initial high-res agentview frame with the correct absolute path |
| Outcome | Success — 258725 B, 1 image returned |
| Mechanism | **verification** (visual grounding input) |

### Turn 7 — 00:43:13 — **>>> HIGHLIGHT 1: re-grounding vs. stored literals begins here**
| | |
|---|---|
| Reasoning | "The salad dressing is the 'Ranch Dressing' bottle (dark, green cap) in the center-top. Let me back-project pixels on it and on the basket interior." |
| Tool calls | `back_project {row:440,col:422,step:0}` (317 B); `back_project {row:455,col:425,step:0}` (317 B); `back_project {row:420,col:420,step:0}` (317 B); `segment {"prompt":"the woven basket","camera":"agentview"}` (629 B) |
| Purpose | Semantically identify the target object among 7 candidates (`alphabet_soup_1, basket_1, cream_cheese_1, ketchup_1, milk_1, salad_dressing_1, tomato_sauce_1` — confirmed in `states.json` `object_names`), then triangulate its world position from three live pixel samples; segment the basket via SAM3 text prompt |
| Outcome | All four calls succeed |
| Mechanism | **semantic grounding** (visual disambiguation vs. distractor groceries) + **localization** (multi-pixel back-projection + SAM3 segmentation) — this is live perception, not the reference recipe's stored `xyz=[-0.185,-0.088,0.20]`; see Audit 3 for the literal-value comparison |

### Turn 8 — 00:43:34
| | |
|---|---|
| Reasoning | "Salad dressing ... confirmed at world ≈ (-0.180, -0.089) ... Basket at (0.077, 0.248). Let me get the basket interior center to avoid rim bias." |
| Tool call | `back_project {row_range:[440,540], col_range:[750,890], step:0}` (523 B, region mode) |
| Purpose | Refine the basket target from a single-pixel estimate to a region-centroid estimate (avoids rim bias) |
| Outcome | Success — basket center refined to (0.077, 0.245) |
| Mechanism | **localization** (region-mode back-projection refinement) |

### Turn 9 — 00:43:44
| | |
|---|---|
| Reasoning | "Now execute the proven approach: position over the salad dressing bottle, grasp-only pi0_pick, carry to basket, release." |
| Tool call | `move_to {xyz:[-0.18,-0.089,0.2], gripper:-1, step_clip:0.025, max_steps:80}` (2204 B) |
| Purpose | Scripted pre-grasp approach over the live-grounded bottle position |
| Outcome | Success (positioned) |
| Mechanism | **staging** (pre-grasp approach, analytic `move_to` primitive) — note `xyz=[-0.18,-0.089,0.2]` is the *live* value, not the reference's `[-0.185,-0.088,0.20]` (see Audit 3) |

### Turn 10 — 00:43:50
| | |
|---|---|
| Tool call | `Read` on `images_wrist_hi/image_wrist_hi_01.png` (148281 B) |
| Purpose | Verify gripper-object alignment via wrist camera before committing to a grasp |
| Outcome | Success — "dark green salad-dressing bottle is centered between the gripper fingers" |
| Mechanism | **verification** (pre-grasp visual check) |

### Turn 11 — 00:44:00
| | |
|---|---|
| Tool call | `pi0_pick {"prompt":"pick up the salad dressing", max_chunks:12, lift_thresh:0.05, gripper_closed_thresh:0.06}` (2539 B) |
| Purpose | Invoke the frozen Pi0.5 VLA, closed-loop, budget-capped at 12 action chunks, for the grasp only |
| Outcome | Success per pi0_pick's own heuristic ("gripper ~0.037 = holding") |
| Mechanism | **bounded VLA invocation** (chunk-capped `pi0_pick` call against the frozen policy) |

### Turn 12 — 00:44:21
| | |
|---|---|
| Tool calls | `Read` on `images_cam_hi/image_cam_hi_02.png` (262853 B) and `images_wrist_hi/image_wrist_hi_02.png` (178973 B) |
| Purpose | Verify the grasp visually (per `feedback_pi0_false_positive_lift.md`'s rule: treat `pi0_pick` success as provisional) |
| Outcome | "Grasp confirmed — the Ranch Dressing bottle is held and the basket is just ahead" |
| Mechanism | **verification** (post-grasp double-check against the VLA's own provisional success flag) |

### Turn 13 — 00:44:32
| | |
|---|---|
| Tool call | `move_to {xyz:[0.077,0.245,0.35], gripper:1, step_clip:0.02, max_steps:100}` (2198 B) |
| Purpose | Carry the held bottle to basket-center xy at carry height 0.35 (gripper held closed, `gripper:1`) |
| Outcome | Success (positioned over basket) |
| Mechanism | **staged transport** (carry leg, first stage) |

### Turn 14 — 00:44:42
| | |
|---|---|
| Tool call | `Read` on `images_wrist_hi/image_wrist_hi_03.png` (180577 B) |
| Purpose | Confirm the bottle is centered over the basket interior before releasing |
| Outcome | "The bottle is over the basket interior" |
| Mechanism | **verification** (pre-release check) |

### Turn 15 — 00:44:48 — **>>> HIGHLIGHT 2: failed-release retry loop begins here**
| | |
|---|---|
| Tool call | `release {max_steps:30}` (1927 B) |
| Purpose | Open gripper to drop the bottle into the basket |
| Outcome | Executes, but `libero_terminated` does NOT fire (release from carry height 0.35 without descending let the tall bottle tip over the rim) |
| Mechanism | **staged transport** (release leg) — attempt 1 |

### Turn 16 — 00:44:57
| | |
|---|---|
| Tool call | `Read` on `images_cam_hi/image_cam_hi_04.png` (263137 B) |
| Purpose | Check whether the predicate's absence means a real miss |
| Outcome | "The bottle fell in front of the basket and is now lying horizontally on the floor — it rolled out." |
| Mechanism | **verification** (terminal-predicate check → detects the miss) |

### Turn 17 — 00:45:10
| | |
|---|---|
| Reasoning | "I can recover within this episode. Let me localize the fallen bottle precisely." |
| Tool calls | `segment {"prompt":"the bottle lying on the floor","camera":"agentview"}` (630 B); `back_project {row:720,col:865,step:4}` (315 B); `back_project {row:760,col:900,step:4}` (315 B) |
| Purpose | Re-localize the object from scratch after the failed release — object pose changed after falling, so the earlier grounding is stale |
| Outcome | Success — "the bottle rolled out and lies horizontally at ~(0.21, 0.27)" |
| Mechanism | **retry** (recovery decision, one-shot/no-reset regime) + **semantic grounding**/**localization** (re-run against the new object pose) |

### Turn 18 — 00:45:59
| | |
|---|---|
| Tool call | `move_to {xyz:[0.213,0.266,0.18], gripper:-1, step_clip:0.02, max_steps:80}` (2197 B) |
| Purpose | Re-stage over the fallen bottle (now upright per reasoning) at low approach height |
| Outcome | Success |
| Mechanism | **staging** (re-approach after failed release) |

### Turn 19 — 00:46:13
| | |
|---|---|
| Tool call | `Read` on `images_wrist_hi/image_wrist_hi_05.png` (135901 B) |
| Purpose | Verify the re-approach alignment via wrist camera |
| Outcome | "The bottle settled upright and is centered between the gripper fingers" |
| Mechanism | **verification** |

### Turn 20 — 00:46:24 — **>>> HIGHLIGHT 3: empty-grasp recovery begins here**
| | |
|---|---|
| Tool call | `pi0_pick {"prompt":"pick up the salad dressing", max_chunks:10, lift_thresh:0.05, gripper_closed_thresh:0.06}` (2536 B) |
| Purpose | Second bounded VLA grasp attempt on the re-localized, fallen bottle |
| Outcome | Ambiguous per raw numbers (see turn 22) |
| Mechanism | **bounded VLA invocation** (2nd chunk-capped `pi0_pick` call) |

### Turn 21 — 00:46:42
| | |
|---|---|
| Tool calls | `Read` on `images_cam_hi/image_cam_hi_06.png` (255721 B) and `images_wrist_hi/image_wrist_hi_06.png` (126925 B) |
| Purpose | Verify the second grasp |
| Outcome | Sets up the miss finding in turn 22 |
| Mechanism | **verification** |

### Turn 22 — 00:46:57
| | |
|---|---|
| Reasoning | "Grasp missed (fingers closed on air/neck). Bottle is still upright on the floor. Let me precisely localize it via the wrist camera and re-center." |
| Tool calls | `back_project {row:650,col:545,camera:"wrist",step:6}` (321 B); `back_project {row:560,col:540,camera:"wrist",step:6}` (323 B) |
| Purpose | Diagnose the empty pi0_pick as a real miss (not the provisional-success false positive from turn 21's images) and re-localize precisely using the close-range wrist camera instead of agentview |
| Outcome | Success — bottle center refined to ~(0.223, 0.296) |
| Mechanism | **verification** (empty-grasp detection) + **localization** (wrist-camera re-localization, finer-grained than agentview) — this is the moment the empty-grasp recovery pivots from VLA-only to analytic fallback |

### Turn 23 — 00:47:12
| | |
|---|---|
| Tool call | `move_to {xyz:[0.223,0.296,0.14], gripper:-1, step_clip:0.02, max_steps:60}` (2198 B) |
| Purpose | Re-center precisely over the bottle at a lower approach height (0.14 vs. the earlier 0.18) using the wrist-refined coordinates |
| Outcome | Success |
| Mechanism | **staging** (precision re-approach) |

### Turn 24 — 00:47:27
| | |
|---|---|
| Tool call | `Read` on `images_wrist_hi/image_wrist_hi_07.png` (657268 B) |
| Purpose | Confirm the bottle neck is centered between the fingers at grasp height |
| Outcome | Confirmed |
| Mechanism | **verification** |

### Turn 25 — 00:47:37
| | |
|---|---|
| Tool call | `set_gripper {gripper:1, steps:10}` (1849 B) |
| Purpose | **Analytic fallback**: after two pi0_pick misses, abandon the VLA grasp primitive and close the gripper directly via the scripted `set_gripper` primitive on the wrist-verified neck position |
| Outcome | "Gripper closed to ~0.027 (holding something)" |
| Mechanism | **retry** (fallback path switch: VLA primitive → analytic primitive) — this is the second half of Highlight 3 |

### Turn 26 — 00:47:47
| | |
|---|---|
| Tool call | `move_to {xyz:[0.189,0.283,0.26], gripper:1, step_clip:0.02, max_steps:80}` (2198 B) |
| Purpose | Lift straight up to confirm the analytic grasp (gripper held closed via `gripper:1`) |
| Outcome | Success |
| Mechanism | **staging** (lift-and-confirm) |

### Turn 27 — 00:47:56
| | |
|---|---|
| Tool call | `Read` on `images_cam_hi/image_cam_hi_09.png` (262165 B) |
| Purpose | Visual confirmation of the analytic grasp + lift |
| Outcome | "Bottle grasped and lifted successfully" |
| Mechanism | **verification** |

### Turn 28 — 00:48:11
| | |
|---|---|
| Tool calls | `set_gripper {gripper:1, steps:6}` (1846 B); `move_to {xyz:[0.077,0.245,0.3], gripper:1, step_clip:0.02, max_steps:80}` (2195 B) |
| Purpose | Firm the grip, then carry over the basket center (re-using the same live-grounded basket xy from turn 8: (0.077, 0.245)) at carry height 0.3 |
| Outcome | Success |
| Mechanism | **staged transport** (grip-firming + carry leg, 2nd attempt) |

### Turn 29 — 00:48:23
| | |
|---|---|
| Tool call | `Read` on `images_wrist_hi/image_wrist_hi_11.png` (174085 B) |
| Purpose | Confirm the bottle is centered over the basket interior before descending |
| Outcome | "Bottle is centered over the basket interior (liner visible below)" |
| Mechanism | **verification** |

### Turn 30 — 00:48:35
| | |
|---|---|
| Tool call | `move_to {xyz:[0.075,0.243,0.22], gripper:1, step_clip:0.015, max_steps:80}` (2200 B) |
| Purpose | **This is the key fix vs. attempt 1**: descend to seat the bottle base *inside* the basket at z=0.22 (below the rim) instead of releasing from carry height 0.35 |
| Outcome | Success — "Bottle base is now seated low in the basket" |
| Mechanism | **staged transport** (descent leg — the staging step attempt 1 skipped) |

### Turn 31 — 00:48:43
| | |
|---|---|
| Tool call | `release {max_steps:30}` (1925 B) |
| Purpose | Open gripper to drop the bottle the final ~few cm into the basket interior |
| Outcome | **`libero_terminated: true`** — confirmed in `states.json` step_idx 13 (see Audit 4) |
| Mechanism | **terminal predicate** (benchmark success signal fires) |

### Turn 32 — 00:49:06
| | |
|---|---|
| Tool calls | `write_text_file` to `object_swap_t2_s0.json` (audit, 185 B result / ~2480+ chars content); `write_text_file` to `recipe_object_swap_t2_s0.jsonl` (recipe, 193 B result / ~1502+ chars content) |
| Purpose | Persist the episode audit and the replayable primitive-command recipe |
| Outcome | Both writes succeed |
| Mechanism | **recipe write** |

### Turn 33 — 00:49:21
| | |
|---|---|
| Tool call | `finish {"status":"success", "summary":"..."}` (879 B) |
| Purpose | Signal task completion to the harness |
| Outcome | `FINISH called` logged; `Claude Agent SDK finished in 437.0s` |
| Mechanism | **control** (finish) |

---

## Summary table

### Primitive/tool invocation counts (from `run.log`, all 51 `[tool->]` calls)

| Tool | Count | Class |
|---|---|---|
| `Read` (Claude Code SDK native) | 13 | control/perception (image ingestion) |
| `back_project` | 8 | perception (localization) |
| `move_to` | 7 | analytic primitive (staging/transport) |
| `read_text_file` | 7 | memory-file IO |
| `pi0_pick` | 2 | VLA primitive (bounded invocation) |
| `release` | 2 | analytic primitive |
| `segment` | 2 | perception (SAM3) |
| `set_gripper` | 2 | analytic primitive |
| `write_text_file` | 2 | memory-file IO |
| `list_dir` | 3 | memory-file IO |
| `Bash` (Claude Code SDK native) | 1 | control (infra recovery) |
| `view_driver_state` | 1 | perception (state view) |
| `finish` | 1 | control |
| **Total tool calls** | **51** | matches harness-reported `tool_calls: 51` |

### Episode-level stats

| Metric | Value | Source |
|---|---|---|
| Planner turns used | 33 (of 60 max) | `transcript_object_swap_t2_s0.json` → `stats.turns_used` |
| Tool calls | 51 | `stats.tool_calls` |
| Wall time (SDK-reported) | 437.0 s | `run.log` line 207 |
| Wall time (harness-reported, incl. teardown) | 439.8 s | `run.log` line 211 |
| Model | `claude-opus-4-8` | `run.log` line 1, 7 |
| Terminal signal | `libero_terminated: true` | `states.json` step_idx 13 (`release` result) — see Audit 4 |
| Recipe length (replayable primitive commands) | 13 lines | `recipe_object_swap_t2_s0.jsonl` |
| Reset invocations | 0 | Audit 2 |
| pi0_pick attempts | 2 (1st carried-but-mis-released grasp; 2nd empty, recovered analytically) | this trace, turns 11 & 20 |

---

## Audits

### 1. Vocabulary audit

**Distinct tools invoked in `run.log`** (13 distinct names, 51 total calls):

| Tool invoked | Class | Registered in `toolkit.py`/`tools.py`? |
|---|---|---|
| `view_driver_state` | perception (state view) | Yes — `LiberoToolkit._register_libero_tools` inspection_handlers, impl in `tools.py::view_driver_state` |
| `read_text_file` | memory-file IO | Yes — common tool, `rpent/tools/common.py` (registered by base `Toolkit._register_common_tools`) |
| `list_dir` | memory-file IO | Yes — common tool, `rpent/tools/common.py` |
| `write_text_file` | memory-file IO | Yes — common tool, `rpent/tools/common.py` |
| `finish` | control | Yes — common tool, `rpent/tools/common.py` |
| `back_project` | perception (localization) | Yes — `LiberoToolkit` inspection_handlers, impl in `tools.py::back_project` |
| `segment` | perception (SAM3) | Yes — `LiberoToolkit` inspection_handlers, bound to `self._primitives.segment` (SAM3 client) |
| `move_to` | analytic primitive | Yes — `LiberoToolkit._register_libero_tools` primitive list, impl `LiberoPrimitives.move_to` |
| `pi0_pick` | VLA primitive | Yes — same list, impl `LiberoPrimitives.pi0_pick` (calls frozen Pi0.5 via `VLAClient.predict_action_batch`) |
| `release` | analytic primitive | Yes — same list, impl `LiberoPrimitives.release` |
| `set_gripper` | analytic primitive | Yes — same list, impl `LiberoPrimitives.set_gripper` |
| `Read` | control/perception (native) | **Not** an RPent-registered tool — it is the Claude Agent SDK's own built-in file-read tool, available because the planner backend is `claude_code` (the SDK ships its own tool belt alongside the MCP-style RPent tools) |
| `Bash` | control (native) | Same as `Read` — native Claude Agent SDK tool, used once for infra path-recovery (turn 5), not an RPent primitive |

**Verdict: nothing invoked is unregistered.** Every LIBERO-domain tool call (`view_driver_state`, `back_project`, `segment`, `move_to`, `pi0_pick`, `release`, `set_gripper`) resolves to an entry in `LiberoToolkit._SPECS` (built from `libero_tools.TOOLS_SPEC` in `RPent/robots/libero/tools.py`), and every file/control tool (`read_text_file`, `write_text_file`, `list_dir`, `finish`) resolves to `rpent/tools/common.py`. `Read` and `Bash` are outside the RPent toolkit entirely — they are the harness's Claude Agent SDK planner backend's native tools, present because `--planner claude_code` was used; they are not part of the LIBERO tool vocabulary and were used only for memory/image IO and one path-recovery shell call, never to touch the environment or the VLA.

**Registered-but-unused this episode** (present in `toolkit.py`/`tools.py` but not invoked in this trace): `pi0_doubled`, `rotate_wrist`, `rotate_pitch`, `move_pose`, `view_camera_meta`. Expected — this task needed no wrist/pitch reorientation or contact-skill primitive.

**Nominal-vs-actual VLA primitive naming.** The internship plan's nominal primitive list is `move_to, move_pose, rotate_wrist, rotate_pitch, set_gripper, release, vla_act` — i.e. it names the single VLA-invocation primitive `vla_act`. The actual repo registers **no tool literally named `vla_act`**. Instead the VLA-invocation surface is split into three named primitives, all implemented in `RPent/robots/libero/tools.py::LiberoPrimitives`:

| Nominal (plan) | Actual (repo) | Notes |
|---|---|---|
| `vla_act` | `pi0_pick` | Closed-loop Pi0.5 grasp primitive; success heuristic = post-descent EEF ascent + gripper closure, or `libero_terminated`. The one actually exercised in this trace (2x). |
| `vla_act` | `pi0_doubled` | Closed-loop Pi0.5 *contact-skill* primitive (knobs/buttons/stoves/pushes) — success mirrors `libero_terminated` only. Registered but not invoked this episode. |
| `vla_act` | (also `place` on `LiberoPrimitives`, **not** in `TOOLS_SPEC` / not tool-registered) | A third VLA-driven method exists in the primitives class (place sub-instruction until release) but is not exposed as an agent tool in `toolkit.py` — it is not part of the live vocabulary at all. |

So the mapping is 1-nominal-name → 2-registered-tools (+1 unregistered helper method), each scoped to a different phase of contact (pick vs. generic contact), rather than one general `vla_act` covering both.

### 2. RESET audit

`grep -ni reset` over `run.log`, `transcript_object_swap_t2_s0.json`, and `claude_object_swap_t2_s0.txt`:

- **Zero** actual reset tool invocations (no `[tool->] reset` line anywhere, and `LiberoToolkit` does not even register a `reset` tool — `primitives.reset()` is called exactly once, internally, by `init_primitives_clean` at harness startup, before the planner sees any turn).
- The only text matches are the planner's own prose, both in `run.log`'s `finish` call and mirrored in the transcript: *"Recovered in-episode (**no reset**)"* — i.e. the planner explicitly self-reports operating in the one-shot regime while executing the mid-episode recovery (Highlight 2/3).

**Verdict: PASSED as expected.** Zero reset invocations, consistent with the `strict_hybrid_guide.md` / `pro_hybrid_guide.md` "single episode, no reset" regime.

### 3. Coordinate-replay audit

Grepped the planner transcript (`transcript_object_swap_t2_s0.json`) and the recipe (`recipe_object_swap_t2_s0.jsonl`) for the reference seed-0 literals documented in the asset study (`/tmp/.../scratchpad/day4_asset_study.md`):

| Reference literal | grep result | Nearest value actually used this run |
|---|---|---|
| `-0.185` (reference pre-grasp x) | **ABSENT** | `-0.18` (turn 9 `move_to`, and recipe line 1) |
| `0.231` (reference carry y) | **ABSENT** | `0.245` (turn 13/28/29/30 basket y — refined via region-mode `back_project`, turn 8) |
| `-0.107, -0.237` (rejected wrong-object literal, ketchup bottle in the reference run) | **ABSENT** | not applicable — this run never mis-identified the ketchup bottle; grounding turn 7 went straight to the correct dark-capped bottle |

**Conclusion:** none of the reference recipe's stored literals appear anywhere in this run's transcript or recipe. Every spatial value used (`-0.18, -0.089, 0.2` pre-grasp; `0.077, 0.245` basket center; `0.213, 0.266` / `0.223, 0.296` for the fallen-bottle recovery) traces back to a live `back_project`/`segment` call earlier in the same turn sequence (turns 7, 8, 17, 22), not to the reference file read in turn 3. This is the expected re-grounding behavior: the reference recipe was consulted only as a **technique** prior (approach → grasp → carry → release skeleton — see turn 9's reasoning, "execute the proven approach"), while every coordinate came from this episode's own perception pipeline.

**Honesty caveat:** this is seed 0, the *same* scene configuration as the reference run, so numeric proximity between `-0.18` and `-0.185`, or `0.245` and `0.231`, is expected and unsurprising — a correct independent perception pipeline run on an identical scene should land close to the same physical point. This audit does not (and cannot, from proximity alone) prove non-replay; what it establishes is the **derivation path**: the values are traceable to this episode's own `back_project`/`segment` tool outputs in the transcript, and the literal reference strings do not appear verbatim. The gap that does appear (`-0.18` vs `-0.185`, `0.245` vs `0.231`, and a genuinely different z/height schedule — this run's staged descent to `z=0.22` inside the basket vs. the reference's single carry-height release) is additional (though not conclusive) evidence of independent re-derivation rather than copy-paste, since a literal replay would reproduce the reference's exact digits and its single-release (non-staged) structure.

### 4. Predicate audit

`states.json` (818 lines, 14 step entries, `step_idx` 0–13) top-level entries carry a `libero_terminated` boolean at every step. The terminal entry:

```json
{
  "step_idx": 13,
  "libero_terminated": true,
  "task_language": "Pick the salad dressing and place it in the basket",
  "command": {"action": "release", "max_steps": 30},
  "result": {
    "name": "release",
    "steps_used": 14,
    "start_gripper_opening": 0.0538,
    "peak_gripper_opening": 0.0775,
    "final_gripper_opening": 0.0775,
    "libero_terminated": true
  },
  "elapsed_s": 0.82
}
```

`object_names` recorded in the same step's `state` block: `["alphabet_soup_1", "basket_1", "cream_cheese_1", "ketchup_1", "milk_1", "salad_dressing_1", "tomato_sauce_1"]` — confirms 7 scene objects including the 6 grocery distractors the planner had to disambiguate against in turn 7.

**Verdict: CONFIRMED.** `libero_terminated: true` is set by `LiberoEnvClient`/`LiberoPrimitives.release` reading the actual benchmark task predicate (the LIBERO env's own success-condition evaluator, e.g. an `On`/`In` object-relation predicate for `object_swap` — not a private heuristic; contrast with `pi0_pick`'s own provisional `success` field, which is a local lift/gripper heuristic distinct from this authoritative field). This is the same field the `pi0_pick`/`release`/`move_to`/`rotate_*`/`move_pose` primitives all surface per-step (`self.env.episode_done`), and it is the terminal one that flips to `true` and stays there — no subsequent step exists in `states.json` after step 13, consistent with the episode ending on this predicate firing.
