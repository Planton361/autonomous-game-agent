---
atlas_workspace_generated: true
atlas_presentation_view: assembly-scope
atlas_presentation_only: true
atlas_registry_revision: sha256:d79ab66332122815cc5651bdd1bf428990ee5fae3c9073f5c85d4aa7b31047d2
---
[[Assets/Excalidraw/Agent Anatomy.excalidraw|← Agent Anatomy]] · **Navigation location:** Agent Anatomy / Observe (static presentation breadcrumb)

**OBSERVE — Observation Integrity / State**

Visible observation boundary, processing and payload.

**Presentation context:** Acquire · **Observe** · Retain / Retrieve
*Presentation-only navigation; it does not describe technical dependencies.*

## Observe landmarks

### No-Spoiler Firewall
Type: `Component` · Stable ID: `CMP-NO-SPOILER-FIREWALL` — Enforces the visible-data and no-spoiler boundary. **Action:** [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|Open No-Spoiler Firewall]]

> **Visible-State Bridge — OPTIONAL**
>
> Type: `Component` · Stable ID: `CMP-VISIBLE-STATE-BRIDGE` — Optional screenshot-bound, allowlisted bridge assistance remains subject to the no-spoiler boundary. **Action:** [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Open Visible-State Bridge]]
>
> Reduced emphasis and proximity are presentation-only; they do not claim Firewall containment.

### Perception
Type: `Component` · Stable ID: `CMP-PERCEPTION` — Assembles signals from visible observations. **Action:** [[Components/CMP-PERCEPTION — Perception|Open Perception]]

### Observation
Type: `DataArtifact` · Stable ID: `DAT-OBSERVATION` — Typed visible-observation payload carrying visible signals and evidence references. **Action:** [[Data Artifacts/DAT-OBSERVATION — Observation|Open Observation]]

## Exact Registry relations

Each row preserves the Registry direction. `part_of` is technical parenthood; `presented_in_domain` is presentation grouping.

| Source | Predicate | Target |
| --- | --- | --- |
| [[Components/CMP-CORTEX — Cortex|Cortex · CMP-CORTEX]] | `consumes` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|Independent Verifier · CMP-INDEPENDENT-VERIFIER]] | `consumes` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Components/CMP-MEMORY — Memory|Memory · CMP-MEMORY]] | `consumes` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] | `contributes_to_function` | [[Functions/FUNC-OBSERVE — Observe|Observe · FUNC-OBSERVE]] |
| [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] | `part_of` | [[Home/SYS-AGA — Autonomous Game Agent Experiment System|Autonomous Game Agent Experiment System · SYS-AGA]] |
| [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] | `presented_in_domain` | [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|Observation Integrity & State · DOM-OBS-INTEGRITY-STATE]] |
| [[Components/CMP-OBSERVATION-BUILDER — Observation Builder|Observation Builder · CMP-OBSERVATION-BUILDER]] | `part_of` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] | `consumes` | [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|ScreenFrame · DAT-SCREEN-FRAME]] |
| [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] | `contributes_to_function` | [[Functions/FUNC-OBSERVE — Observe|Observe · FUNC-OBSERVE]] |
| [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] | `part_of` | [[Home/SYS-AGA — Autonomous Game Agent Experiment System|Autonomous Game Agent Experiment System · SYS-AGA]] |
| [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] | `presented_in_domain` | [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|Observation Integrity & State · DOM-OBS-INTEGRITY-STATE]] |
| [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] | `supplies` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Components/CMP-PERCEPTION-UI-STATE — UI State Classification|UI State Classification · CMP-PERCEPTION-UI-STATE]] | `part_of` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Components/CMP-TEMPORAL-STATE — Temporal State|Temporal State · CMP-TEMPORAL-STATE]] | `consumes` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] | `contributes_to_function` | [[Functions/FUNC-ACQUIRE — Acquire|Acquire · FUNC-ACQUIRE]] |
| [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] | `observes` | [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|Game / Environment · ENV-GAME-INSTANCE]] |
| [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] | `part_of` | [[Home/SYS-AGA — Autonomous Game Agent Experiment System|Autonomous Game Agent Experiment System · SYS-AGA]] |
| [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] | `presented_in_domain` | [[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|Environment & Acquisition · DOM-ENV-ACQUISITION]] |
| [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] | `contributes_to_function` | [[Functions/FUNC-OBSERVE — Observe|Observe · FUNC-OBSERVE]] |
| [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] | `presented_in_domain` | [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|Observation Integrity & State · DOM-OBS-INTEGRITY-STATE]] |
| [[Evidence/EVID-48-BRIDGE — Bridge — baseline inspection|Bridge — baseline inspection · EVID-48-BRIDGE]] | `supports` | [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] |
| [[Evidence/EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection|Bridge sanitizer — baseline inspection · EVID-48-BRIDGE-SANITIZER]] | `supports` | [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] |
| [[Evidence/EVID-48-BRIDGE-SANITIZER — Bridge sanitizer — baseline inspection|Bridge sanitizer — baseline inspection · EVID-48-BRIDGE-SANITIZER]] | `supports` | [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] |
| [[Evidence/EVID-48-BUILDER — Builder — baseline inspection|Builder — baseline inspection · EVID-48-BUILDER]] | `supports` | [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] |
| [[Evidence/EVID-48-BUILDER — Builder — baseline inspection|Builder — baseline inspection · EVID-48-BUILDER]] | `supports` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|Canonical Ingress · EVID-48-CANON-INGRESS]] | `supports` | [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] |
| [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|Canonical Ingress · EVID-48-CANON-INGRESS]] | `supports` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|Canonical Ingress · EVID-48-CANON-INGRESS]] | `supports` | [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|Optional Visible-State Bridge · CMP-VISIBLE-STATE-BRIDGE]] |
| [[Evidence/EVID-48-CANON-INGRESS — Canonical Ingress|Canonical Ingress · EVID-48-CANON-INGRESS]] | `supports` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Evidence/EVID-48-FIREWALL — Firewall — baseline inspection|Firewall — baseline inspection · EVID-48-FIREWALL]] | `supports` | [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|No-Spoiler Firewall · CMP-NO-SPOILER-FIREWALL]] |
| [[Evidence/EVID-48-OBSERVATION — Observation — baseline inspection|Observation — baseline inspection · EVID-48-OBSERVATION]] | `supports` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |
| [[Evidence/EVID-48-OCR-LIMIT — Ocr Limit — baseline inspection|Ocr Limit — baseline inspection · EVID-48-OCR-LIMIT]] | `supports` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Evidence/EVID-48-SPATIAL-LIMIT — Spatial Limit — baseline inspection|Spatial Limit — baseline inspection · EVID-48-SPATIAL-LIMIT]] | `supports` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Evidence/EVID-48-TEST-OBSERVATION — Test Observation — baseline inspection|Test Observation — baseline inspection · EVID-48-TEST-OBSERVATION]] | `supports` | [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] |
| [[Evidence/EVID-48-TEST-OBSERVATION — Test Observation — baseline inspection|Test Observation — baseline inspection · EVID-48-TEST-OBSERVATION]] | `supports` | [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] |

The Registry declares no Bridge → Firewall → Perception pipeline edge. The order above is presentation-only.

## Technical endpoint lanes

Only direct Registry relations from the four selected landmarks can populate these lanes.

### Interfaces

No directly related endpoint of this type is mapped for the four selected landmarks.

### Contracts

No directly related endpoint of this type is mapped for the four selected landmarks.

### DataArtifacts

- [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|ScreenFrame · DAT-SCREEN-FRAME]] · `DataArtifact` — [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] `consumes` → [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|ScreenFrame · DAT-SCREEN-FRAME]]
- [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]] · `DataArtifact` — [[Components/CMP-PERCEPTION — Perception|Perception · CMP-PERCEPTION]] `supplies` → [[Data Artifacts/DAT-OBSERVATION — Observation|Observation · DAT-OBSERVATION]]

### MeasurementPoints

No directly related endpoint of this type is mapped for the four selected landmarks.

## Existing W05 Observation detail

The W05 detail files are available in the private derived Workspace; this public-safe fallback does not link into that private output.

## Research attached to listed technical subjects

Research navigation is derived from exact listed technical subjects. No Research → Observe edge, Domain inheritance, descendant expansion, or Assembly-level relevance is created.

### Direct Registry Research Question relations

No direct Registry Research Question relation is declared for these exact subjects.

### Eligible declared literature navigation

Private declared-reference paths are unavailable in this public-safe fallback; no private Research content is read or copied here.

These paths are navigation only; they do not establish evidence, coverage, novelty, completeness, consensus, a gap, or an accepted scientific claim.

## Authority, revision and limitations

- Generated Registry model revision: `sha256:d79ab66332122815cc5651bdd1bf428990ee5fae3c9073f5c85d4aa7b31047d2`.
- This Markdown scope is a presentation/navigation view, not a Registry identity, technical parent or Component Hub.
- Exact Registry records and relations remain authoritative; this view creates no technical relation or scientific status.
- The four-landmark selection is fixed for this reference slice; Temporal State is not an Observe landmark.
