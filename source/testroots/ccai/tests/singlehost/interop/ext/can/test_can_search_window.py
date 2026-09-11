"""
    Tests for :class:`CanSearchWindow` driven directly, without a bus: evidence is added
    the way the presence monitor loop adds it.
"""

from datetime import datetime, timedelta

import gc

from ccai import testbase

from ccai.interop.ext.can.cancoordinator import CanCoordinator
from ccai.interop.ext.can.candeviceevidence import CanDeviceEvidence
from ccai.interop.ext.can.canpresence import CanPresence
from ccai.interop.ext.can.cansearchwindow import CanSearchWindow


LONG_WINDOW = 10.0
SHORT_WINDOW = 0.2
FAST_POLL = 0.02
WAIT_TIMEOUT = 15.0


def make_presence() -> CanPresence:
    """
        Creates an unstarted presence for a window to reference.  A real presence is
        used because the window holds it through a weak reference.

        :returns: The presence.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")
    presence = CanPresence(coordinator)
    return presence


def make_window(presence: CanPresence, window_length: float, limit_to: list = None) -> CanSearchWindow:
    """
        Creates a window that opens now and closes after ``window_length`` seconds.

        :param presence: The owning presence.
        :param window_length: The window's life in seconds.
        :param limit_to: The arbitration ids the window is waiting for, if any.

        :returns: The window, not yet started.
    """
    start = datetime.now()
    end = start + timedelta(seconds=window_length)
    window = CanSearchWindow(presence, "window-under-test", start, end, FAST_POLL, limit_to=limit_to)
    return window


def test_id_property() -> None:
    """
        The window reports the id it was created with.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)

    testbase.assert_equal(window.id, "window-under-test")

    return


def test_is_active_false_before_start() -> None:
    """
        A window is inactive until it is started.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)

    testbase.assert_false(window.is_active())

    return


def test_wait_before_start_raises() -> None:
    """
        Waiting on a window that was never started is an error.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)

    with testbase.raises(RuntimeError):
        window.wait(timeout=0.1)

    return


def test_start_makes_window_active() -> None:
    """
        Once started, the window reports itself active.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW, limit_to=[0x10])

    window.start()

    testbase.assert_true(window.is_active())

    return


def test_window_times_out() -> None:
    """
        A window whose end time passes closes on its own.
    """
    presence = make_presence()
    window = make_window(presence, SHORT_WINDOW, limit_to=[0x10])
    window.start()

    closed = window.wait(timeout=WAIT_TIMEOUT)

    testbase.assert_true(closed)
    testbase.assert_false(window.is_active())

    return


def test_wait_returns_false_while_still_open() -> None:
    """
        A bounded wait on a window that has not closed returns False.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW, limit_to=[0x10])
    window.start()

    closed = window.wait(timeout=0.1)

    testbase.assert_false(closed)
    testbase.assert_true(window.is_active())

    return


def test_window_completes_when_limit_satisfied() -> None:
    """
        Evidence for every id in ``limit_to`` closes the window and fills ``matching_devices``.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW, limit_to=[0x10])
    window.start()

    evidence = CanDeviceEvidence(0x10, data=b"\x01")
    window.add_evidence(evidence)

    closed = window.wait(timeout=WAIT_TIMEOUT)
    testbase.assert_true(closed)
    testbase.assert_false(window.is_active())

    matching = window.matching_devices
    testbase.assert_equal(list(matching.keys()), [0x10])
    testbase.assert_true(matching[0x10] is evidence)

    return


def test_partial_match_keeps_window_open() -> None:
    """
        Evidence for some of ``limit_to`` is recorded as matching but does not close the
        window; the rest closes it.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW, limit_to=[0x10, 0x20])
    window.start()

    window.add_evidence(CanDeviceEvidence(0x10))
    still_open = window.wait(timeout=0.2)
    testbase.assert_false(still_open)
    testbase.assert_equal(list(window.matching_devices.keys()), [0x10])

    window.add_evidence(CanDeviceEvidence(0x20))
    closed = window.wait(timeout=WAIT_TIMEOUT)
    testbase.assert_true(closed)

    matching = sorted(list(window.matching_devices.keys()))
    testbase.assert_equal(matching, [0x10, 0x20])

    return


def test_wait_after_close_returns_true_immediately() -> None:
    """
        Waiting on an already closed window returns at once.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW, limit_to=[0x10])
    window.start()
    window.add_evidence(CanDeviceEvidence(0x10))
    window.wait(timeout=WAIT_TIMEOUT)

    closed = window.wait(timeout=0)

    testbase.assert_true(closed)

    return


def test_add_evidence_keyed_by_arbitration_id() -> None:
    """
        Evidence is stored under its arbitration id, and newer evidence replaces older.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)

    older = CanDeviceEvidence(0x10, data=b"\x01")
    newer = CanDeviceEvidence(0x10, data=b"\x02")
    window.add_evidence(older)
    window.add_evidence(newer)

    found = window.devices_found
    testbase.assert_equal(list(found.keys()), [0x10])
    testbase.assert_true(found[0x10] is newer)

    return


def test_devices_found_returns_a_copy() -> None:
    """
        Mutating the returned mapping does not change the window.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)
    window.add_evidence(CanDeviceEvidence(0x10))

    found = window.devices_found
    found.clear()

    testbase.assert_equal(list(window.devices_found.keys()), [0x10])

    return


def test_presence_property_returns_owner() -> None:
    """
        The window hands back the presence that owns it.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)

    testbase.assert_true(window.presence is presence)

    return


def test_presence_reference_is_weak() -> None:
    """
        The window does not keep its presence alive; once the owner is gone the
        property returns None.
    """
    presence = make_presence()
    window = make_window(presence, LONG_WINDOW)

    del presence
    gc.collect()

    testbase.assert_true(window.presence is None)

    return
