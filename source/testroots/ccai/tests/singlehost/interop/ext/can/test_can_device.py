"""
    Tests for :class:`CanDevice` over python-can's in-process ``virtual`` interface.
"""

from ccai import testbase
from ccai.testbase.properties import run_property, strategies as st

from ccai.interop.ext.can.cancoordinator import CanCoordinator
from ccai.interop.ext.can.candevice import CanDevice
from ccai.testshared.interop.ext.can.virtualbus import VirtualCanBus


# The largest 11-bit (standard) arbitration id and the smallest that needs 29 bits.
MAX_STANDARD_ID = 0x7FF
MIN_EXTENDED_ID = 0x800
MAX_EXTENDED_ID = 0x1FFFFFFF


# ----------------------------------------------------------------------
# send
# ----------------------------------------------------------------------

def test_send_list_payload_reaches_peer() -> None:
    """
        A list payload sent through the device arrives at the peer.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        device = CanDevice(coordinator, 0x123)

        device.send([1, 2, 3])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x123)
        testbase.assert_equal(bytes(received.data), b"\x01\x02\x03")

    return


def test_send_bytes_payload_reaches_peer() -> None:
    """
        A bytes payload sent through the device arrives at the peer.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        device = CanDevice(coordinator, 0x123)

        device.send(b"\x0a\x0b")

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(bytes(received.data), b"\x0a\x0b")

    return


def test_send_standard_id_on_wire() -> None:
    """
        A device with an 11-bit id sends standard frames.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        device = CanDevice(coordinator, 0x123)

        device.send([1])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_false(received.is_extended_id)

    return


def test_send_explicit_extended_id_on_wire() -> None:
    """
        An explicit extended flag is carried on the wire.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        device = CanDevice(coordinator, 0x12345678, is_extended_id=True)

        device.send([1])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x12345678)
        testbase.assert_true(received.is_extended_id)

    return


def test_send_inferred_extended_id_on_wire() -> None:
    """
        An id above 11 bits is sent as an extended frame without being told to.
    """
    with VirtualCanBus() as vbus:
        coordinator = vbus.create_coordinator(connect=True)
        device = CanDevice(coordinator, 0x12345678)

        device.send([1])

        received = vbus.recv_on_peer()
        testbase.assert_true(received is not None)
        testbase.assert_equal(received.arbitration_id, 0x12345678)
        testbase.assert_true(received.is_extended_id)

    return


def test_send_while_disconnected_raises() -> None:
    """
        Sending through a device whose coordinator is not connected raises.
    """
    coordinator = CanCoordinator(channel="never-connected", bustype="virtual")
    device = CanDevice(coordinator, 0x123)

    with testbase.raises(RuntimeError):
        device.send([1, 2, 3])

    return


# ----------------------------------------------------------------------
# Extended-id inference
# ----------------------------------------------------------------------

def test_extended_id_inference_max_standard_id() -> None:
    """
        0x7FF is the last id that fits in 11 bits, so it is not extended.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, MAX_STANDARD_ID)

    testbase.assert_false(device.is_extended_id)

    return


def test_extended_id_inference_first_extended_id() -> None:
    """
        0x800 is the first id that needs more than 11 bits, so it is extended.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, MIN_EXTENDED_ID)

    testbase.assert_true(device.is_extended_id)

    return


def test_extended_id_inference_zero() -> None:
    """
        Id zero is a standard id.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, 0)

    testbase.assert_false(device.is_extended_id)

    return


def test_explicit_false_overrides_inference() -> None:
    """
        An explicit ``is_extended_id=False`` wins over the width of the id.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, MIN_EXTENDED_ID, is_extended_id=False)

    testbase.assert_false(device.is_extended_id)

    return


def test_explicit_true_overrides_inference() -> None:
    """
        An explicit ``is_extended_id=True`` wins over the width of the id.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, 0x123, is_extended_id=True)

    testbase.assert_true(device.is_extended_id)

    return


def test_extended_id_inference_property() -> None:
    """
        For every id in the 29-bit range, inference says extended exactly when the
        id does not fit in 11 bits.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    def check(arbitration_id: int) -> None:
        device = CanDevice(coordinator, arbitration_id)
        expected = arbitration_id > MAX_STANDARD_ID
        testbase.assert_equal(device.is_extended_id, expected)
        return

    examples = run_property(check, max_examples=200,
                            arbitration_id=st.integers(min_value=0, max_value=MAX_EXTENDED_ID))

    testbase.assert_greater(examples, 0)

    return


# ----------------------------------------------------------------------
# Properties and repr
# ----------------------------------------------------------------------

def test_arbitration_id_property() -> None:
    """
        The device reports the id it was created with.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, 0x123)

    testbase.assert_equal(device.arbitration_id, 0x123)

    return


def test_repr_names_id_and_flag() -> None:
    """
        The repr shows the id in hex and the extended flag.
    """
    coordinator = CanCoordinator(channel="unused", bustype="virtual")

    device = CanDevice(coordinator, 0x123)

    testbase.assert_equal(repr(device), "CanDevice(id=0x123, ext=False)")

    return
