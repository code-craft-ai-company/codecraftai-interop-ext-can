"""
    Tests for :class:`CanPresence` lifecycle and discovery over python-can's in-process
    ``virtual`` interface.  Frames are put on the wire by the fixture's peer bus, so the
    monitor loop reads real python-can messages rather than mocks.
"""

from datetime import datetime

from ccai import testbase

from ccai.interop.ext.can.cancoordinator import CanCoordinator
from ccai.interop.ext.can.canpresence import CanPresence
from ccai.testshared.interop.ext.can.virtualbus import (
    VirtualCanBus,
    count_presence_monitor_threads,
    join_presence_monitor_threads,
)


# Windows that must close by matching get a long life so a slow runner cannot
# expire them first; the poll interval is short so completion is noticed quickly.
LONG_WINDOW = 10.0
FAST_POLL = 0.02
WAIT_TIMEOUT = 15.0


# ----------------------------------------------------------------------
# start / stop
# ----------------------------------------------------------------------

def test_start_starts_one_monitor_thread() -> None:
    """
        Starting a presence adds exactly one monitor thread.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        before = count_presence_monitor_threads()

        presence = vbus.create_presence(coordinator=coordinator, start=True)

        after = count_presence_monitor_threads()
        testbase.assert_equal(after - before, 1)

        presence.stop()

    return


def test_start_is_idempotent() -> None:
    """
        A second start does not start a second monitor thread.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        before = count_presence_monitor_threads()
        presence = vbus.create_presence(coordinator=coordinator, start=True)

        presence.start()

        after = count_presence_monitor_threads()
        testbase.assert_equal(after - before, 1)

    return


def test_stop_ends_monitor_thread() -> None:
    """
        After stop, the monitor thread exits on its own.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        before = count_presence_monitor_threads()
        presence = vbus.create_presence(coordinator=coordinator, start=True)

        presence.stop()

        still_alive = join_presence_monitor_threads()
        testbase.assert_equal(still_alive, 0)
        testbase.assert_equal(count_presence_monitor_threads(), before)

    return


def test_stop_is_idempotent() -> None:
    """
        A second stop is accepted without error.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)

        presence.stop()
        presence.stop()

        with testbase.raises(RuntimeError):
            presence.discover_devices(window_length=0.1)

    return


def test_stop_before_start_is_noop() -> None:
    """
        Stopping a presence that never started does nothing.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")
    presence = CanPresence(coordinator)

    presence.stop()

    with testbase.raises(RuntimeError):
        presence.discover_devices(window_length=0.1)

    return


def test_restart_after_stop_monitors_again() -> None:
    """
        A presence stopped and started again sees new frames.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        presence.stop()
        join_presence_monitor_threads()

        presence.start()
        window = presence.discover_devices(limit_to=[0x42], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)
        vbus.send_from_peer(0x42, [1])

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)
        testbase.assert_true(0x42 in window.matching_devices)

    return


# ----------------------------------------------------------------------
# discover_devices
# ----------------------------------------------------------------------

def test_discover_devices_requires_start() -> None:
    """
        Opening a window before start is refused.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")
    presence = CanPresence(coordinator)

    with testbase.raises(RuntimeError):
        presence.discover_devices(window_length=0.1)

    return


def test_discovery_sees_frame_from_virtual_bus() -> None:
    """
        A frame the peer puts on the wire appears in the window with its payload.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x123], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x123, b"\x01\x02")

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)

        found = window.devices_found
        testbase.assert_true(0x123 in found)

        evidence = found[0x123]
        testbase.assert_equal(bytes(evidence.data), b"\x01\x02")
        testbase.assert_false(evidence.is_extended_id)

    return


def test_discovery_evidence_timestamp_comes_from_frame() -> None:
    """
        The evidence timestamp is the frame's wire timestamp, which the virtual bus
        stamps at send time, so it falls between the send and the check.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x123], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        before = datetime.now()
        vbus.send_from_peer(0x123, [1])
        window.wait(timeout=WAIT_TIMEOUT)
        after = datetime.now()

        evidence = window.devices_found[0x123]
        testbase.assert_true(before <= evidence.timestamp)
        testbase.assert_true(evidence.timestamp <= after)

    return


def test_discovery_records_extended_id_frame() -> None:
    """
        An extended frame is recorded with its 29-bit id and the extended flag.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x12345678], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x12345678, [1], is_extended_id=True)

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)

        evidence = window.devices_found[0x12345678]
        testbase.assert_true(evidence.is_extended_id)

    return


def test_discovery_keeps_latest_evidence_for_repeated_id() -> None:
    """
        When a device speaks twice, the window holds its most recent payload.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x200], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x100, b"\x01")
        vbus.send_from_peer(0x100, b"\x02")
        vbus.send_from_peer(0x200, b"\x03")

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)

        evidence = window.devices_found[0x100]
        testbase.assert_equal(bytes(evidence.data), b"\x02")

    return


def test_two_windows_see_the_same_frame() -> None:
    """
        Every open window is notified of a frame.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        first = presence.discover_devices(limit_to=[0x5], window_length=LONG_WINDOW,
                                          monitor_interval=FAST_POLL)
        second = presence.discover_devices(limit_to=[0x5], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x5, [5])

        first_closed = first.wait(timeout=WAIT_TIMEOUT)
        second_closed = second.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(first_closed)
        testbase.assert_true(second_closed)
        testbase.assert_true(0x5 in first.matching_devices)
        testbase.assert_true(0x5 in second.matching_devices)

    return
