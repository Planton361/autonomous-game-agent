# No-Spoiler and Network-Isolation Protocol

## Principle

The agent may learn only from information a player could observe on screen during the run and from
outcomes of its own logged actions. Convenience, debugging value, or technical availability does
not turn hidden state into admissible evidence.

This protocol applies to researchers, automation, prompts, models, logs, bridge code, analysis, and
manual annotations used by the pilot.

## Run-mode classification

### `screen-only`

Primary official mode. Runtime inputs are pixels/screenshots, OCR derived from those pixels, input
execution results, and memories derived from prior admissible run evidence. No bridge is active.

### `bridge-assisted`

Official auxiliary mode. Screenshots remain mandatory. A bridge may add only strictly allowlisted
fields that encode information simultaneously visible to the player, such as visible message text,
visible menu items, UI visibility flags, screen positions of visible sprites, visible visual
hashes, and screenshot ID. Sanitization occurs before Observation or persistence. Results form a
separate cohort.

### `debug`

Non-official development mode for diagnostics and synthetic/offline fixtures. The no-hidden-state
rule still applies. Debug tooling may add timing or component traces, but these traces cannot be
used as game knowledge. Exposure to hidden state or spoiler content immediately changes the label
to `contaminated`.

### `contaminated`

Permanent quarantine label for a run or derived artifact whose epistemic integrity is broken or
uncertain. Contaminated data may be retained for incident analysis but is excluded from model
memory, training data, baselines, confirmatory metrics, and official screenshots/reports. It is
never cleaned by deleting the offending field and relabeling the run.

## Allowed evidence

- screenshots or screen recordings captured from the game window;
- OCR text visibly present in linked screenshots;
- allowlisted bridge-assisted representations of simultaneously visible information;
- visible outcomes observed after logged primitive actions;
- uncertainty-bearing perception outputs derived solely from allowed pixels;
- facts and risk estimates derived from the agent's own admissible evidence, with evidence IDs.

Sanitized bridge data is assistance to perception, not privileged truth. When it conflicts with the
screen, retain both artifacts, mark the observation uncertain, and stop using the field until
reviewed.

## Forbidden sources

- RPG Maker map data, internal map/event IDs or names, event comments or trigger conditions;
- game switches, variables, scripts, databases, exact enemy HP/statistics/resistances, unobserved
  item effects, ending/quest flags, savegame internals, process memory, or RAM-derived state;
- wiki pages, walkthroughs, maps, guides, videos, forum/Discord hints, search results, remote agents,
  or human hints based on spoiler knowledge;
- filenames, source symbols, debug overlays, accessibility trees, or telemetry that reveal facts
  not simultaneously visible to an ordinary player;
- pretraining retrieval or remote model calls during the run. A local model's fixed prior is part
  of the declared model condition, but it may not be prompted to recall game-specific guide
  knowledge; unsupported claims remain hypotheses and cannot enter Memory as facts.

The firewall must reject and log forbidden fields, not silently discard and continue an official
run.

## Network isolation

Official runs are offline. Before the run:

1. install dependencies and place the exact local model, prompts, configs, fixtures, and tools on
   the machine;
2. disable network interfaces or enforce an OS/container deny-all egress and ingress policy;
3. verify that the LLM endpoint resolves locally and that telemetry/update checks are disabled;
4. record isolation method, verification command/result, timestamp, and operator in the manifest;
5. start a new run directory only after the seal is verified.

During the run, web browsing, package installation, remote inference, cloud logging, telemetry,
NTP-dependent decisions, messaging, and remote storage are forbidden. A monotonic local clock is
used for budgets. Reconnecting for any reason ends the run and marks it contaminated.

After the run, stop all automation and seal hashes before reconnecting. Artifacts may then be moved
for analysis, but no newly retrieved spoiler material may be joined to the admissible dataset.
Dependency/model downloads happen outside runs and create a new recorded environment version.

## Bridge firewall

The allowlist is deny-by-default. Allowed fields and types are versioned and hashed with the run
configuration. Unknown fields are rejected. Forbidden field attempts generate a security event,
stop the run, and contaminate it even if downstream code did not use the value. Raw pre-sanitized
bridge payloads must not enter normal logs, prompts, Memory, training data, or screenshots metadata.

Screen-only runs must fail preflight if any bridge process, import path, connection, or active flag
is detected. Bridge-assisted runs require synchronized screenshot evidence for every accepted
payload. Debug mode cannot be used to bypass these requirements.

## Human and model hygiene

Operators and reviewers must not consult external Fear & Hunger knowledge while preparing start
states, monitoring runs, or labeling outcomes. An operator may use only the visible start-state
card and safety instructions. Manual intervention is limited to emergency stop and documented
environment recovery; strategic hints invalidate the run.

Prompts contain architecture/no-spoiler instructions and admissible evidence only. Memory retrieval
filters by run integrity, evidence provenance, and mode. Contaminated/debug artifacts are excluded
from Cortex context and Body training by default.

## Required provenance

Before the first observation, record:

- full Git commit, branch, dirty flag, and diff hash when dirty;
- SHA-256 of exact ordered prompt bytes;
- SHA-256 of canonical resolved configuration bytes;
- model name/version and SHA-256 of the local model artifact or deterministic shard manifest;
- run mode, experiment version, condition, seed, host/runtime identity;
- network-isolation method and verification evidence;
- firewall/allowlist version and hash.

If a large sharded model cannot be hashed as one file, hash every shard and then hash the canonical
ordered `(relative_path, sha256, size)` manifest. Model name alone is insufficient.

## Incident and contamination procedure

On suspected exposure:

1. stop input immediately without replanning;
2. preserve logs and the last visible screenshot; do not copy hidden payload values into normal
   evidence;
3. record incident time, source category, affected run/artifacts, and reporter;
4. label the run `contaminated` and propagate quarantine to derived memories, datasets, and model
   checkpoints;
5. determine the earliest affected artifact and invalidate descendants;
6. fix the boundary under a separate ticket and demonstrate it with synthetic forbidden-field
   tests before another official run.

Uncertainty is resolved toward contamination. Contaminated runs stay visible in accounting so the
violation rate cannot be improved by deletion.
