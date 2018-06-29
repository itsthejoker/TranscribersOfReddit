from unittest.mock import MagicMock
import importlib
import threading

import celery


# This is intended to be global, but it will break spectacularly if we fork the
# individual tests. This means we need to create the registry of signatures as a
# global scoped only to the thread.
t_lock = threading.local()
t_lock.signature_mocks = {}


def reset_signatures():
    """
    Clears out the global registry of task signatures. Should be done in between
    each test to give a clean-room environment.
    """
    t_lock.signature_mocks.clear()


def assert_valid_import_path(pypath):
    parts = pypath.split(".")
    task = parts.pop()
    parent = ".".join(parts)

    # @see https://stackoverflow.com/a/14050282
    spec = importlib.util.find_spec(parent)
    assert spec is not None, f"Module {parent} does not resolve to a valid module"

    mod = importlib.import_module(parent)
    assert hasattr(mod, task), f"Module {parent} does not have a {task} task"


def signature(pypath, *args, **kwargs):
    """Mock of the ``celery.signature`` method"""
    key = hash((pypath, tuple(args), tuple(kwargs)))

    try:
        out = t_lock.signature_mocks[key]
    except KeyError:
        # Only run this as we're creating new mocks
        assert_valid_import_path(pypath)

        out = MagicMock(name=pypath, spec=celery.Signature)
        t_lock.signature_mocks[key] = out

    return out


def assert_no_tasks_called():
    """
    Semantic helper for asserting task did not call any subsequent tasks
    """
    assert_only_tasks_called()


def assert_only_tasks_called(*signatures):
    """
    Semantic helper for asserting only the tasks with the given signatures were
    called. This helps with mapping which task signatures upon which the tested
    task depends.
    """
    if (
        len(signatures) > 0
        and not isinstance(signatures[0], str)
        and hasattr(signatures[0], "__iter__")
    ):
        # Incorrect usage. Correct a some tuple/list/dict/etc. from first arg as
        # all args instead.
        return assert_only_tasks_called(*signatures[0])

    skips = [signature(task) for task in signatures]
    for task in t_lock.signature_mocks.values():
        if task in skips:
            continue

        task.delay.assert_not_called()
        task.apply_async.assert_not_called()
