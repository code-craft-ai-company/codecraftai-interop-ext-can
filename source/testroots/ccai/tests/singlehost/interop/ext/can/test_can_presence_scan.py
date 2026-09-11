"""
    Scan semantics of :class:`CanPresence` search windows over python-can's in-process
    ``virtual`` interface: duplicate collapsing, ``limit_to`` filtering and expiry.
"""

from ccai import testbase

from ccai.testshared.interop.ext.can.virtualbus import VirtualCanBus


LONG_WINDOW = 10.0
SHORT_WINDOW = 0.3
FAST_POLL = 0.02
WAIT_TIMEOUT = 15.0


def test_scan_collapses_repeated_arbitration_id() -> None:
    """
        A repeated arbitration id collapses to a single discovered device.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x100, 0x200], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x100, [1])
        vbus.send_from_peer(0x100, [2])
        vbus.send_from_peer(0x200, [3])

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)

        detected = sorted(list(window.devices_found.keys()))
        testbase.assert_equal(detected, [0x100, 0x200])

    return


def test_limit_to_completes_when_every_id_is_seen() -> None:
    """
        A window with ``limit_to`` closes as soon as all listed ids have spoken.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x100, 0x200], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x100, [1])
        vbus.send_from_peer(0x200, [2])

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)
        testbase.assert_false(window.is_active())

        matching = sorted(list(window.matching_devices.keys()))
        testbase.assert_equal(matching, [0x100, 0x200])

    return


def test_limit_to_filters_matching_devices() -> None:
    """
        Devices outside ``limit_to`` are recorded as found but never as matching.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x100], window_length=LONG_WINDOW,
                                           monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x300, [3])
        vbus.send_from_peer(0x200, [2])
        vbus.send_from_peer(0x100, [1])

        closed = window.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(closed)

        matching = sorted(list(window.matching_devices.keys()))
        testbase.assert_equal(matching, [0x100])

        found = sorted(list(window.devices_found.keys()))
        testbase.assert_equal(found, [0x100, 0x200, 0x300])

    return


def test_search_window_expires_silent_device() -> None:
    """
        A window waiting on an id that never speaks closes when its time is up, with
        nothing matched and nothing found.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x999], window_length=SHORT_WINDOW,
                                           monitor_interval=FAST_POLL)

        closed = window.wait(timeout=WAIT_TIMEOUT)

        testbase.assert_true(closed)
        testbase.assert_false(window.is_active())
        testbase.assert_equal(window.matching_devices, {})
        testbase.assert_equal(window.devices_found, {})

    return


def test_search_window_without_limit_closes_on_expiry() -> None:
    """
        A window with no ``limit_to`` cannot complete by matching; it collects what it
        hears and closes when its time is up.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(window_length=SHORT_WINDOW, monitor_interval=FAST_POLL)

        vbus.send_from_peer(0x111, [1])

        closed = window.wait(timeout=WAIT_TIMEOUT)

        testbase.assert_true(closed)
        testbase.assert_false(window.is_active())
        testbase.assert_true(0x111 in window.devices_found)
        testbase.assert_equal(window.matching_devices, {})

    return


def test_expired_window_ignores_late_frames() -> None:
    """
        A frame that arrives after the window closed is not added to it.
    """
    with VirtualCanBus() as vbus:
        presence = vbus.create_presence(start=True)
        window = presence.discover_devices(limit_to=[0x999], window_length=SHORT_WINDOW,
                                           monitor_interval=FAST_POLL)
        window.wait(timeout=WAIT_TIMEOUT)

        vbus.send_from_peer(0x999, [1])

        # Prove the late frame was processed by the monitor loop: a fresh window
        # that waits for a later frame closes only after the loop has moved past
        # the late one, because frames are read in order.
        follow_up = presence.discover_devices(limit_to=[0x998], window_length=LONG_WINDOW,
                                              monitor_interval=FAST_POLL)
        vbus.send_from_peer(0x998, [2])
        follow_up_closed = follow_up.wait(timeout=WAIT_TIMEOUT)
        testbase.assert_true(follow_up_closed)

        testbase.assert_equal(window.devices_found, {})

    return
