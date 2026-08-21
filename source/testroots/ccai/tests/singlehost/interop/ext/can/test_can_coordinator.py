from ccai import testbase

from unittest.mock import MagicMock, patch
import can
from ccai.interop.ext.can.cancoordinator import CanCoordinator

# ----------------------------------------------------------------------
# TestCanCoordinator
# ----------------------------------------------------------------------


def test_connect() -> None:
    with patch('can.Bus') as mock_bus_cls:
        coord = CanCoordinator(channel='vcan0')
        coord.connect()
        mock_bus_cls.assert_called_with(channel='vcan0', bustype='virtual', bitrate=500000)
        coord.disconnect()
        testbase.assert_true(coord._bus is None)

    return

def test_send_message() -> None:
    with patch('can.Bus') as mock_bus_cls:
        mock_bus = MagicMock()
        mock_bus_cls.return_value = mock_bus
        coord = CanCoordinator(channel='vcan0')
        coord.connect()

        coord.send_message(0x123, [1, 2, 3])
        mock_bus.send.assert_called()
        args, _ = mock_bus.send.call_args
        msg = args[0]
        testbase.assert_equal(msg.arbitration_id, 0x123)
        testbase.assert_equal(list(msg.data), [1, 2, 3])

    return

def test_send_message_not_connected():
    coord = CanCoordinator(channel='vcan0')
    with testbase.raises(RuntimeError):
        coord.send_message(0x123, [1, 2, 3])

def test_receive_message() -> None:
    with patch('can.Bus') as mock_bus_cls:
        mock_bus = MagicMock()
        mock_bus_cls.return_value = mock_bus
        expected_msg = can.Message(arbitration_id=0x456, data=[4, 5, 6])
        mock_bus.recv.return_value = expected_msg

        coord = CanCoordinator(channel='vcan0')
        coord.connect()

        msg = coord.receive_message(timeout=0.1)
        testbase.assert_equal(msg, expected_msg)
        mock_bus.recv.assert_called_with(0.1)

    return
