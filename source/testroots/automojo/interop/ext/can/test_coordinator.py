import unittest
from unittest.mock import MagicMock, patch
import can
from automojo.interop.ext.can.cancoordinator import CanCoordinator

class TestCanCoordinator(unittest.TestCase):

    @patch('can.Bus')
    def test_connect(self, mock_bus_cls):
        coord = CanCoordinator(channel='vcan0')
        coord.connect()
        mock_bus_cls.assert_called_with(channel='vcan0', bustype='virtual', bitrate=500000)
        coord.disconnect()
        self.assertIsNone(coord._bus)

    @patch('can.Bus')
    def test_send_message(self, mock_bus_cls):
        mock_bus = MagicMock()
        mock_bus_cls.return_value = mock_bus
        coord = CanCoordinator(channel='vcan0')
        coord.connect()

        coord.send_message(0x123, [1, 2, 3])
        mock_bus.send.assert_called()
        args, _ = mock_bus.send.call_args
        msg = args[0]
        self.assertEqual(msg.arbitration_id, 0x123)
        self.assertEqual(list(msg.data), [1, 2, 3])

    def test_send_message_not_connected(self):
        coord = CanCoordinator(channel='vcan0')
        with self.assertRaises(RuntimeError):
            coord.send_message(0x123, [1, 2, 3])

    @patch('can.Bus')
    def test_receive_message(self, mock_bus_cls):
        mock_bus = MagicMock()
        mock_bus_cls.return_value = mock_bus
        expected_msg = can.Message(arbitration_id=0x456, data=[4, 5, 6])
        mock_bus.recv.return_value = expected_msg

        coord = CanCoordinator(channel='vcan0')
        coord.connect()

        msg = coord.receive_message(timeout=0.1)
        self.assertEqual(msg, expected_msg)
        mock_bus.recv.assert_called_with(0.1)

if __name__ == "__main__":
    unittest.main()
