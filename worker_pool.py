# -*- coding: utf-8 -*-
"""
worker_pool.py - Bounding ThreadPool for background tasks in Bobys Salon Billing V5.6

Phase 3B FIX: Centralizes long-running background work into a bounded pool
instead of spawning unbounded threads from every module. This prevents:
  - Thread explosion on low-end PCs (caps concurrent workers)
  - Memory pressure from many concurrent backup/sync/report threads
  - Untracked background work with no error visibility

Usage:
    from worker_pool import submit_background_task, wait_worker_done

    # Fire-and-forget with optional callback
    submit_background_task(
        fn=my_heavy_function,
        args=(arg1, arg2),
        label="sync_to_folder",       # for logging/diagnostics
        on_done=lambda ok, err: messagebox.showinfo("Done", "OK"),
        on_error=lambda err: app_log(f"[bg failed] {err}"),
    )
"""
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Tuple, Any, Optional

# Phase 3B: Cap at 3 concurrent workers. On low-end machines this prevents
# CPU thrashing from simultaneous backup + sync + report + WA sends.
_MAX_WORKERS = 3

_executor: Optional[ThreadPoolExecutor] = None
_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """Lazily created, shared thread pool."""
    global _executor
    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=_MAX_WORKERS,
                    thread_name_prefix="SalonBG",
                )
    return _executor


def submit_background_task(
    fn: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    label: str = "unnamed",
    on_done: Callable | None = None,
    on_error: Callable | None = None,
) -> Future:
    """Submit a callable to the bounded background worker pool.

    Args:
        fn: Callable to run in a background thread
        args: Positional args for fn
        kwargs: Keyword args for fn
        label: Human-readable label for logging/diagnostics
        on_done: Optional callback(future) called on success in calling thread
        on_error: Optional callback(error) called on failure in calling thread

    Returns:
        concurrent.futures.Future - caller can wait() or cancel()

    Phase 3B FIX: All background work flows through this single pool,
    bounded to _MAX_WORKERS concurrent threads.
    """
    kwargs = kwargs or {}

    def _wrapper():
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            _log(f"[worker_pool:{label}] failed: {exc}")
            if on_error:
                try:
                    on_error(exc)
                except Exception as cb_err:
                    _log(f"[worker_pool:{label}] on_error callback failed: {cb_err}")
            raise

    executor = _get_executor()
    future = executor.submit(_wrapper)

    if on_done:
        future.add_done_callback(lambda f: _safe_callback(on_done, f, label))

    _log(f"[worker_pool:{label}] submitted (pool active: {executor._work_queue.qsize()})")
    return future


def _safe_callback(cb: Callable, future: Future, label: str):
    """Run optional callback with error suppression."""
    try:
        cb(future)
    except Exception as cb_err:
        _log(f"[worker_pool:{label}] callback error: {cb_err}")


def get_pool_stats() -> dict:
    """Return current pool diagnostics."""
    executor = _get_executor()
    return {
        "max_workers": _MAX_WORKERS,
        "queued": executor._work_queue.qsize(),
        "active": threading.active_count(),
    }


def wait_worker_done(timeout: float = 30.0):
    """Wait for all pending background tasks to finish.

    Phase 3B FIX: Used during shutdown to prevent data loss
    from in-progress backups/syncs.
    """
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None


def _log(msg: str):
    """Log to app_debug.log without importing utils (avoid circular)."""
    try:
        from utils import app_log
        app_log(msg)
    except Exception:
        pass
