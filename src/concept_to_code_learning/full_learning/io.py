"""Keep local storage off the event loop and settle writes before cancellation."""

import asyncio
import threading
from contextlib import suppress

from .errors import LearningError


class CommitGate:
    def __init__(self):
        self.lock = threading.Lock()
        self.started = False
        self.cancelled = False

    def start(self):
        # The lock covers only this decision, never disk IO. Cancellation either
        # wins before COMMIT, or observes that completion has already won.
        with self.lock:
            if self.cancelled:
                raise LearningError("CANCELLED", "request", "请求已取消，未保存迟到结果。", 409)
            self.started = True

    def cancel(self):
        with self.lock:
            self.cancelled = not self.started
            return self.cancelled


async def run_commit(function, *args):
    gate = CommitGate()
    task = asyncio.create_task(asyncio.to_thread(function, *args, commit_gate=gate))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled = gate.cancel()
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if cancelled:
            with suppress(Exception):
                task.result()
            raise
        # COMMIT won the boundary: return its actual outcome, never claim that
        # a successfully stored answer was cancelled without saving.
        return task.result()


async def run_io(function, *args, **kwargs):
    return await settle(asyncio.create_task(asyncio.to_thread(function, *args, **kwargs)))


async def settle(task):
    """Finish bounded owned work before propagating cancellation to its caller."""
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # Threads cannot be cancelled. Do not let a transaction or staging write
        # outlive its caller's cleanup or its request's terminal state.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        with suppress(Exception):
            task.result()
        raise
