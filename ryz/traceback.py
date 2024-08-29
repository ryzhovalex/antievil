"""
Tools for working with traceback.
"""
import copy
import inspect
import traceback
import types
from typing import TypeVar


def fmt_stack_summary(summary: traceback.StackSummary) -> str:
    return "".join(
        list(traceback.StackSummary.from_list(summary).format())).strip()

def get_as_str(err: Exception) -> str | None:
    s = None
    tb = err.__traceback__
    if tb:
        summary = traceback.extract_tb(tb)
        s = fmt_stack_summary(summary)
    return s

def set(
    err: Exception,
    skip_frames: int = 0,
    ignore_existing: bool = False,
):
    """
    Creates traceback for an err.

    If ``ignore_existing`` is true, and err already has a traceback, it will
    be overwritten. Otherwise for errs with traceback nothing will be done.

    Original err is not affected, modified err is returned. If nothing is done,
    the same err is returned without copying.

    Argument ``skip_frames`` defines how many frames to skip. This function
    or any nested function frames are automatically skipped.
    """
    if err.__traceback__ is not None:
        if not ignore_existing:
            # return the same instance, as nothing was done
            return err
        err.__traceback__ = None

    prev_tb: types.TracebackType | None = new(skip_frames + 1)

    err.__traceback__ = prev_tb
    return err

def new(skip_frames: int = 0) -> types.TracebackType | None:
    current_frame = inspect.currentframe()
    if current_frame is None:
        raise ValueError("unavailable to retrieve current frame")
    # always skip the current frame, additionally skip as many frames as
    # provided by skip_frames
    next_frame = current_frame
    while skip_frames > 0:
        if next_frame is None:
            raise ValueError(f"cannot skip {skip_frames} frames")
        next_frame = next_frame.f_back
        skip_frames -= 1

    prev_tb = None
    while next_frame is not None:
        tb = types.TracebackType(
            tb_next=None,
            tb_frame=next_frame,
            tb_lasti=next_frame.f_lasti,
            tb_lineno=next_frame.f_lineno)
        if prev_tb is not None:
            tb.tb_next = prev_tb
        prev_tb = tb
        next_frame = next_frame.f_back
    return prev_tb
