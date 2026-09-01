"""Thin point-and-click adapter for the offline spatial annotation workflow.

The session and coordinate transform are deliberately independent from Tk so they
remain usable in headless tests.  Tk is imported only by ``launch_spatial_annotation_ui``.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import EllipsisType

from fh_agent.evals.spatial_annotation_review import (
    SpatialAnnotationWorkflow,
    record_spatial_annotation,
)
from fh_agent.evals.spatial_perception_corpus import CorpusSplit, SpatialPerceptionCorpusFrame
from fh_agent.evals.spatial_perception_dataset import (
    AnnotationStatus,
    SpatialPerceptionFrameAnnotation,
)

ScreenPoint = tuple[int, int]


@dataclass(frozen=True, slots=True)
class PpmDisplayTransform:
    """Map a Tk PPM subimage's pixel coordinates back to original PPM pixels."""

    original_width: int
    original_height: int
    subsample_factor: int = 1
    display_x: int = 0
    display_y: int = 0

    def __post_init__(self) -> None:
        if self.original_width <= 0 or self.original_height <= 0:
            msg = "original image dimensions must be positive"
            raise ValueError(msg)
        if self.subsample_factor <= 0:
            msg = "subsample_factor must be positive"
            raise ValueError(msg)

    @property
    def display_width(self) -> int:
        """Return the exact width produced by Tk ``PhotoImage.subsample``."""

        return _ceiling_divide(self.original_width, self.subsample_factor)

    @property
    def display_height(self) -> int:
        """Return the exact height produced by Tk ``PhotoImage.subsample``."""

        return _ceiling_divide(self.original_height, self.subsample_factor)

    @classmethod
    def fitted_to(
        cls,
        *,
        original_width: int,
        original_height: int,
        max_display_width: int,
        max_display_height: int,
        display_x: int = 0,
        display_y: int = 0,
    ) -> "PpmDisplayTransform":
        """Choose one deterministic integer subsampling factor that fits the image."""

        if max_display_width <= 0 or max_display_height <= 0:
            msg = "maximum display dimensions must be positive"
            raise ValueError(msg)
        factor = max(
            1,
            _ceiling_divide(original_width, max_display_width),
            _ceiling_divide(original_height, max_display_height),
        )
        return cls(
            original_width=original_width,
            original_height=original_height,
            subsample_factor=factor,
            display_x=display_x,
            display_y=display_y,
        )

    def display_to_original(self, point: ScreenPoint) -> ScreenPoint | None:
        """Return the original PPM pixel represented by a display click, if any.

        Tk subsampling retains source pixel ``display_coordinate * factor``.  The
        final display pixel is clamped for dimensions not divisible by the factor.
        The right and bottom display edges are intentionally outside the image.
        """

        display_point_x, display_point_y = point
        local_x = display_point_x - self.display_x
        local_y = display_point_y - self.display_y
        if not (0 <= local_x < self.display_width and 0 <= local_y < self.display_height):
            return None
        return (
            min(self.original_width - 1, local_x * self.subsample_factor),
            min(self.original_height - 1, local_y * self.subsample_factor),
        )


@dataclass(frozen=True, slots=True)
class SpatialAnnotationFrameState:
    """The one visible corpus frame and point-only annotation shown by the UI."""

    frame: SpatialPerceptionCorpusFrame
    split: CorpusSplit
    annotation: SpatialPerceptionFrameAnnotation

    @property
    def sequence_id(self) -> str:
        return self.frame.sequence_id

    @property
    def frame_index(self) -> int:
        return self.frame.frame_index

    @property
    def frame_id(self) -> str:
        return self.frame.frame_id


class SpatialAnnotationSession:
    """Pure local annotation state which persists only through domain revision logic."""

    def __init__(self, workflow: SpatialAnnotationWorkflow) -> None:
        self._workflow = workflow
        self._frames = _ordered_frame_states(workflow)
        if not self._frames:
            msg = "spatial annotation workflow contains no corpus frames"
            raise ValueError(msg)
        self._frame_index = 0
        self._drafts: dict[str, SpatialPerceptionFrameAnnotation] = {}
        self._history: dict[str, list[SpatialPerceptionFrameAnnotation]] = {}

    @property
    def workflow(self) -> SpatialAnnotationWorkflow:
        """Return the latest persisted workflow state."""

        return self._workflow

    @property
    def can_mutate(self) -> bool:
        """Frozen corpus versions are view-only."""

        return self._workflow.freeze_record is None

    @property
    def current(self) -> SpatialAnnotationFrameState:
        """Return the deterministic current frame and its draft or persisted annotation."""

        state = self._frames[self._frame_index]
        draft = self._drafts.get(state.frame_id)
        if draft is None:
            return state
        return SpatialAnnotationFrameState(
            frame=state.frame,
            split=state.split,
            annotation=draft,
        )

    @property
    def has_unsaved_changes(self) -> bool:
        """Return whether the displayed frame has an in-memory annotation revision."""

        return self.current.frame_id in self._drafts

    def next_frame(self) -> bool:
        """Move to the next deterministic frame, if one exists."""

        if self._frame_index + 1 >= len(self._frames):
            return False
        self._frame_index += 1
        return True

    def previous_frame(self) -> bool:
        """Move to the previous deterministic frame, if one exists."""

        if self._frame_index == 0:
            return False
        self._frame_index -= 1
        return True

    def set_player_point(self, point: ScreenPoint | None) -> None:
        """Set or clear the one optional player point for the current frame."""

        if point is not None:
            self._assert_original_point(point)
        annotation = self.current.annotation
        self._stage(
            _annotation_with(
                annotation,
                player_screen_position=point,
            )
        )

    def add_sprite_point(self, point: ScreenPoint) -> None:
        """Append one visible sprite point without assigning it an identity or class."""

        self._assert_original_point(point)
        annotation = self.current.annotation
        self._stage(
            _annotation_with(
                annotation,
                visible_sprite_positions=(*annotation.visible_sprite_positions, point),
            )
        )

    def remove_sprite_point(self, index: int = -1) -> None:
        """Remove one sprite point, defaulting to the most recently added point."""

        annotation = self.current.annotation
        points = annotation.visible_sprite_positions
        if not points:
            msg = "current annotation has no visible sprite points to remove"
            raise ValueError(msg)
        normalized_index = index if index >= 0 else len(points) + index
        if normalized_index < 0 or normalized_index >= len(points):
            msg = "sprite point index is outside the current annotation"
            raise IndexError(msg)
        self._stage(
            _annotation_with(
                annotation,
                visible_sprite_positions=(
                    *points[:normalized_index],
                    *points[normalized_index + 1 :],
                ),
            )
        )

    def set_status(self, status: AnnotationStatus) -> None:
        """Set the point-only annotation status without changing review records."""

        self._stage(_annotation_with(self.current.annotation, status=status))

    def undo(self) -> bool:
        """Restore the previous local draft state for the current frame, if available."""

        self._assert_mutable()
        frame_id = self.current.frame_id
        history = self._history.get(frame_id)
        if not history:
            return False
        self._drafts[frame_id] = history.pop()
        return True

    def save_current(
        self,
        persist: Callable[[SpatialAnnotationWorkflow], object] | None = None,
    ) -> SpatialAnnotationWorkflow:
        """Persist the current explicit revision through ``record_spatial_annotation``.

        ``persist`` is supplied by the CLI/UI adapter and is called before this
        session advances its in-memory persisted workflow.  This avoids a UI-only
        JSON mutation path and leaves existing output overwrite policy in the CLI.
        """

        self._assert_mutable()
        frame_id = self.current.frame_id
        annotation = self._drafts.get(frame_id)
        if annotation is None:
            return self._workflow
        revised_workflow = record_spatial_annotation(
            self._workflow,
            annotation,
            overwrite=True,
        )
        if persist is not None:
            persist(revised_workflow)
        self._workflow = revised_workflow
        self._drafts.pop(frame_id, None)
        self._history.pop(frame_id, None)
        self._frames = _ordered_frame_states(revised_workflow)
        return revised_workflow

    def _stage(self, annotation: SpatialPerceptionFrameAnnotation) -> None:
        self._assert_mutable()
        frame_id = self.current.frame_id
        self._history.setdefault(frame_id, []).append(self.current.annotation)
        self._drafts[frame_id] = annotation

    def _assert_mutable(self) -> None:
        if not self.can_mutate:
            msg = (
                "corpus version is frozen; create a new corpus version before revising annotations"
            )
            raise ValueError(msg)

    def _assert_original_point(self, point: ScreenPoint) -> None:
        point_x, point_y = point
        frame = self.current.frame
        if not (0 <= point_x < frame.width and 0 <= point_y < frame.height):
            msg = "point must be a coordinate inside the current original PPM image"
            raise ValueError(msg)


def launch_spatial_annotation_ui(
    session: SpatialAnnotationSession,
    *,
    corpus_root: Path,
    persist: Callable[[SpatialAnnotationWorkflow], object],
) -> None:
    """Open the optional Tk PPM annotator; import Tk only when a desktop is requested."""

    import tkinter as tk
    from tkinter import messagebox

    _SpatialAnnotationTkApp(tk, messagebox, session, corpus_root, persist).run()


class _SpatialAnnotationTkApp:
    """Small Tk adapter around the pure session; it never writes JSON itself."""

    _MAX_DISPLAY_WIDTH = 1100
    _MAX_DISPLAY_HEIGHT = 700

    def __init__(
        self,
        tk: object,
        messagebox: object,
        session: SpatialAnnotationSession,
        corpus_root: Path,
        persist: Callable[[SpatialAnnotationWorkflow], object],
    ) -> None:
        self._tk = tk
        self._messagebox = messagebox
        self._session = session
        self._corpus_root = corpus_root
        self._persist = persist
        self._click_mode = "player"
        self._root = tk.Tk()
        self._root.title("Offline Spatial Point Annotation")
        self._info = tk.StringVar()
        self._message = tk.StringVar()
        self._canvas = tk.Canvas(self._root, highlightthickness=0)
        self._photo: object | None = None
        self._transform: PpmDisplayTransform | None = None
        self._build_controls()
        self._canvas.bind("<Button-1>", self._on_canvas_click)
        self._render_current()

    def run(self) -> None:
        """Run Tk's event loop after all GUI setup is complete."""

        self._root.mainloop()

    def _build_controls(self) -> None:
        tk = self._tk
        tk.Label(self._root, textvariable=self._info, justify="left").pack(anchor="w")
        self._canvas.pack(anchor="w")
        tk.Label(self._root, textvariable=self._message, justify="left").pack(anchor="w")
        controls = tk.Frame(self._root)
        controls.pack(anchor="w")
        self._edit_buttons = (
            tk.Button(controls, text="Set player point", command=self._set_player_mode),
            tk.Button(controls, text="Add sprite point", command=self._set_sprite_mode),
            tk.Button(controls, text="Clear player", command=self._clear_player),
            tk.Button(controls, text="Remove last sprite", command=self._remove_last_sprite),
            tk.Button(controls, text="Undo", command=self._undo),
            tk.Button(controls, text="Usable", command=lambda: self._set_status("usable")),
            tk.Button(controls, text="Uncertain", command=lambda: self._set_status("uncertain")),
            tk.Button(controls, text="Exclude", command=lambda: self._set_status("exclude")),
            tk.Button(controls, text="Save", command=self._save),
        )
        for button in self._edit_buttons:
            button.pack(side="left")
        tk.Button(controls, text="Previous frame", command=self._previous).pack(side="left")
        tk.Button(controls, text="Next frame", command=self._next).pack(side="left")
        if not self._session.can_mutate:
            for button in self._edit_buttons:
                button.configure(state="disabled")

    def _render_current(self) -> None:
        tk = self._tk
        state = self._session.current
        self._transform = PpmDisplayTransform.fitted_to(
            original_width=state.frame.width,
            original_height=state.frame.height,
            max_display_width=self._MAX_DISPLAY_WIDTH,
            max_display_height=self._MAX_DISPLAY_HEIGHT,
        )
        original_photo = tk.PhotoImage(
            file=str(self._corpus_root / state.frame.relative_frame_path),
            format="PPM",
        )
        self._photo = (
            original_photo.subsample(
                self._transform.subsample_factor,
                self._transform.subsample_factor,
            )
            if self._transform.subsample_factor > 1
            else original_photo
        )
        self._canvas.configure(
            width=self._transform.display_width,
            height=self._transform.display_height,
        )
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self._render_overlays(state.annotation)
        draft_suffix = " (unsaved)" if self._session.has_unsaved_changes else ""
        frozen_suffix = "; frozen view only" if not self._session.can_mutate else ""
        self._info.set(
            "\n".join(
                (
                    f"sequence ID: {state.sequence_id}    split: {state.split}",
                    f"frame index: {state.frame_index}    frame ID: {state.frame_id}",
                    f"annotation status: {state.annotation.status}{draft_suffix}{frozen_suffix}",
                )
            )
        )

    def _render_overlays(self, annotation: SpatialPerceptionFrameAnnotation) -> None:
        if annotation.player_screen_position is not None:
            self._draw_point(annotation.player_screen_position, color="#2f6fed")
        for point in annotation.visible_sprite_positions:
            self._draw_point(point, color="#e07a1f")

    def _draw_point(self, original_point: ScreenPoint, *, color: str) -> None:
        assert self._transform is not None
        display_x = original_point[0] // self._transform.subsample_factor
        display_y = original_point[1] // self._transform.subsample_factor
        radius = 4
        self._canvas.create_oval(
            display_x - radius,
            display_y - radius,
            display_x + radius,
            display_y + radius,
            outline=color,
            width=2,
        )

    def _on_canvas_click(self, event: object) -> None:
        assert self._transform is not None
        point = self._transform.display_to_original((event.x, event.y))
        if point is None:
            self._message.set("Click is outside the displayed image.")
            return
        try:
            if self._click_mode == "player":
                self._session.set_player_point(point)
            else:
                self._session.add_sprite_point(point)
        except ValueError as error:
            self._message.set(str(error))
            return
        self._message.set(f"Recorded {self._click_mode} point at original pixel {point}.")
        self._render_current()

    def _set_player_mode(self) -> None:
        self._click_mode = "player"
        self._message.set("Click the displayed image to set or replace the player point.")

    def _set_sprite_mode(self) -> None:
        self._click_mode = "sprite"
        self._message.set("Click the displayed image to add a visible sprite point.")

    def _clear_player(self) -> None:
        self._run_edit(lambda: self._session.set_player_point(None))

    def _remove_last_sprite(self) -> None:
        self._run_edit(self._session.remove_sprite_point)

    def _undo(self) -> None:
        if self._session.undo():
            self._message.set("Reverted the last local edit for this frame.")
            self._render_current()
        else:
            self._message.set("No local edit is available to undo for this frame.")

    def _set_status(self, status: AnnotationStatus) -> None:
        self._run_edit(lambda: self._session.set_status(status))

    def _run_edit(self, edit: Callable[[], object]) -> None:
        try:
            edit()
        except (IndexError, ValueError) as error:
            self._message.set(str(error))
            return
        self._render_current()

    def _previous(self) -> None:
        if not self._session.previous_frame():
            self._message.set("Already at the first corpus frame.")
            return
        self._render_current()

    def _next(self) -> None:
        if not self._session.next_frame():
            self._message.set("Already at the last corpus frame.")
            return
        self._render_current()

    def _save(self) -> None:
        try:
            self._session.save_current(self._persist)
        except (OSError, ValueError) as error:
            self._messagebox.showerror("Could not save annotation", str(error))
            return
        self._message.set(
            "Saved through the annotation revision workflow. Reviews remain unchanged."
        )
        self._render_current()


def _ordered_frame_states(
    workflow: SpatialAnnotationWorkflow,
) -> tuple[SpatialAnnotationFrameState, ...]:
    annotations = {
        annotation.frame_id: annotation
        for sequence in workflow.manifest.annotations.sequences
        for annotation in sequence.frames
    }
    return tuple(
        SpatialAnnotationFrameState(
            frame=frame,
            split=sequence.split,
            annotation=annotations[frame.frame_id],
        )
        for sequence in sorted(workflow.manifest.sequences, key=lambda item: item.sequence_id)
        for frame in sequence.ordered_frames()
    )


def _annotation_with(
    annotation: SpatialPerceptionFrameAnnotation,
    *,
    status: AnnotationStatus | None = None,
    player_screen_position: ScreenPoint | None | EllipsisType = ...,
    visible_sprite_positions: tuple[ScreenPoint, ...] | None = None,
) -> SpatialPerceptionFrameAnnotation:
    """Construct a validated revision instead of bypassing strict Pydantic validation."""

    player_point = (
        annotation.player_screen_position
        if player_screen_position is ...
        else player_screen_position
    )
    return SpatialPerceptionFrameAnnotation(
        frame_id=annotation.frame_id,
        evidence_id=annotation.evidence_id,
        status=annotation.status if status is None else status,
        player_screen_position=player_point,
        visible_sprite_positions=(
            annotation.visible_sprite_positions
            if visible_sprite_positions is None
            else visible_sprite_positions
        ),
    )


def _ceiling_divide(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor
