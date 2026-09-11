"""
    Tests for :class:`CanCoordinator` over python-can's in-process ``virtual`` interface.

    A :class:`VirtualCanBus` provides a peer bus on a private channel; frames the
    coordinator sends arrive at the peer and frames the peer sends arrive at the
    coordinator, with no adapter and no mocking of the bus.
"""

from unittest.mock import patch

import can
from can.interfaces.virtual import VirtualBus

from ccai import testbase

from ccai.interop.ext.can.cancoordinator import CanCoordinator
from ccai.testshared.interop.ext.can.virtualbus import VirtualCanBus


# ----------------------------------------------------------------------
# Connection lifecycle
# ----------------------------------------------------------------------

def test_connect_then_send_reaches_peer() -> None:
    """
        A connected coordinator's frames arrive on the bus.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.send_message(0x123, [1, 2, 3])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x123)

    return


def test_connect_twice_is_safe() -> None:
    """
        Calling connect a second time leaves a working connection.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        coordinator.connect()

        coordinator.send_message(0x321, [9])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x321)

        vbus.send_from_peer(0x111, [1])
        inbound = coordinator.receive_message(timeout=2.0)
        testbase.assert_true(inbound is not None)
        testbase.assert_equal(inbound.arbitration_id, 0x111)

    return


def test_disconnect_leaves_coordinator_unusable() -> None:
    """
        After disconnect, sending is refused until connect is called again.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.disconnect()

        with testbase.raises(RuntimeError):
            coordinator.send_message(0x123, [1, 2, 3])

    return


def test_disconnect_without_connect_is_noop() -> None:
    """
        Disconnecting a coordinator that never connected does nothing.
    """
    coordinator = CanCoordinator(channel="never-connected", bustype="virtual")

    coordinator.disconnect()

    with testbase.raises(RuntimeError):
        coordinator.receive_message(timeout=0.01)

    return


def test_disconnect_twice_is_noop() -> None:
    """
        A second disconnect does nothing.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.disconnect()
        coordinator.disconnect()

        with testbase.raises(RuntimeError):
            coordinator.send_message(0x123, [1])

    return


def test_connect_unknown_interface_raises_can_error() -> None:
    """
        python-can's error for an unknown interface propagates out of connect, and the
        coordinator stays disconnected.
    """
    coordinator = CanCoordinator(channel="nowhere", bustype="no-such-interface")

    with testbase.raises(can.CanError):
        coordinator.connect()

    with testbase.raises(RuntimeError):
        coordinator.send_message(0x123, [1])

    return


# ----------------------------------------------------------------------
# send_message
# ----------------------------------------------------------------------

def test_send_message_list_payload_reaches_peer() -> None:
    """
        A list payload arrives byte for byte.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.send_message(0x123, [1, 2, 3])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(bytes(received.data), b"\x01\x02\x03")

    return


def test_send_message_bytes_payload_reaches_peer() -> None:
    """
        A bytes payload arrives byte for byte.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.send_message(0x123, b"\xde\xad\xbe\xef")

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(bytes(received.data), b"\xde\xad\xbe\xef")

    return


def test_send_message_standard_id_by_default() -> None:
    """
        Without the extended flag the frame goes out with an 11-bit id.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.send_message(0x7FF, [1])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x7FF)
        testbase.assert_false(received.is_extended_id)

    return


def test_send_message_extended_id_reaches_peer() -> None:
    """
        The extended-id flag is carried on the wire.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        coordinator.send_message(0x12345678, [1], is_extended_id=True)

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x12345678)
        testbase.assert_true(received.is_extended_id)

    return


def test_send_message_not_connected_raises() -> None:
    """
        Sending before connect is a RuntimeError, not a python-can error.
    """
    coordinator = CanCoordinator(channel="never-connected", bustype="virtual")

    with testbase.raises(RuntimeError):
        coordinator.send_message(0x123, [1, 2, 3])

    return


def test_send_message_bus_failure_propagates() -> None:
    """
        A python-can send failure is re-raised to the caller.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        with patch.object(VirtualBus, "send", side_effect=can.CanOperationError("simulated bus failure")):
            with testbase.raises(can.CanError):
                coordinator.send_message(0x123, [1])

    return


# ----------------------------------------------------------------------
# receive_message
# ----------------------------------------------------------------------

def test_receive_message_returns_peer_frame() -> None:
    """
        A frame sent by the peer is returned with its id and payload intact.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        vbus.send_from_peer(0x456, [4, 5, 6])

        received = coordinator.receive_message(timeout=2.0)
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x456)
        testbase.assert_equal(bytes(received.data), b"\x04\x05\x06")

    return


def test_receive_message_timeout_returns_none() -> None:
    """
        A silent bus yields None after the timeout rather than raising.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)

        received = coordinator.receive_message(timeout=0.05)

        testbase.assert_true(received is None)

    return


def test_receive_message_not_connected_raises() -> None:
    """
        Receiving before connect is a RuntimeError.
    """
    coordinator = CanCoordinator(channel="never-connected", bustype="virtual")

    with testbase.raises(RuntimeError):
        coordinator.receive_message(timeout=0.01)

    return
