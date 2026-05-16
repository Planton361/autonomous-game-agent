from enum import StrEnum


class PrimitiveAction(StrEnum):
    """Universal low-level actions understood by the input executor."""

    MOVE_UP_SHORT = "move_up_short"
    MOVE_DOWN_SHORT = "move_down_short"
    MOVE_LEFT_SHORT = "move_left_short"
    MOVE_RIGHT_SHORT = "move_right_short"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    OPEN_MENU = "open_menu"
    WAIT = "wait"
