"""Bounded public reader copy from existing source inspections, never runtime authority.

Prototype locators remain EVID-48-BUILDER / OCR-LIMIT / SPATIAL-LIMIT / UI.
Inspected again for #122 at main 80b6b122; no architecture or Registry change.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalReader:
    responsibility: str
    mechanism: str
    inputs: str
    outputs: str
    implementation: str
    limitations: str


PROTOTYPES = {
    "CMP-PERCEPTION": TechnicalReader(
        "Turns visible screen information into an evidence-linked observation for the agent.",
        "Observation Builder sanitizes optional visible bridge fields, computes a frame signature, "
        "requests OCR, classifies the UI, normalizes visible sprites and "
        "assembles the observation.",
        "A captured screen frame, its screenshot evidence, optional allowlisted visible bridge "
        "fields and the last action result.",
        "An Observation containing visible text, UI state, frame signature, sprite information "
        "and evidence links.",
        "The observation assembly and deterministic UI rules are implemented. "
        "The overall perception capability is partial; source inspection "
        "does not certify live performance.",
        "Pixel-to-text OCR is not implemented by the current empty/static backends. "
        "Spatial prediction has a typed interface, but no pixel detector is implemented there. "
        "UI classification can return unknown and is not a validated pixel classifier.",
    ),
    "CMP-OBSERVATION-BUILDER": TechnicalReader(
        "Coordinates the construction of one observation and keeps its visible signals linked "
        "to screenshot evidence.",
        "Sanitize bridge fields; compute the frame signature; call the configured OCR engine; "
        "classify the UI; normalize visible sprites; assemble the typed observation.",
        "A screen frame, screenshot evidence, optional bridge data and an "
        "optional last action result.",
        "One Observation with UI state, text spans, visible message text, sprite information "
        "and screenshot evidence links.",
        "Observation assembly is implemented with an injectable OCR "
        "engine and a deny-by-default firewall. "
        "Source inspection is separate from live verification.",
        "The default OCR engine returns no text. This orchestration does not itself provide "
        "a learned perception backend or independent outcome verification.",
    ),
    "CMP-PERCEPTION-UI-STATE": TechnicalReader(
        "Classifies visible UI signals and reports unknown when they are insufficient.",
        "Checks explicit visible death, combat, menu and dialogue signals, then text spans "
        "and visible positions, using deterministic rules.",
        "Sanitized visible bridge fields and OCR text spans.",
        "A UI state classification with confidence and an evidence link.",
        "Deterministic classification rules are implemented.",
        "This is not a validated pixel classifier. Insufficient visible signals produce unknown.",
    ),
}
