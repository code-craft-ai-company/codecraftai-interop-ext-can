import unittest
from unittest.mock import MagicMock
from automojo.interop.ext.can.cancoordinator import CanCoordinator
from automojo.interop.ext.can.candevice import CanDevice

class TestCanDevice(unittest.TestCase):
    def test_send(self):
        coord = MagicMock(spec=CanCoordinator)
        # Use standard ID to verify default behavior
        device = CanDevice(coord, 0x123)

        device.send([1, 2, 3])

        # Expect is_extended_id=False by default (implicit)
        coord.send_message.assert_called_with(0x123, [1, 2, 3], is_extended_id=False)

    def test_send_extended_id_explicit(self):
        coord = MagicMock(spec=CanCoordinator)
        ext_id = 0x12345678

        # Initialize with explicit flag
        device = CanDevice(coord, ext_id, is_extended_id=True)

        self.assertTrue(device.is_extended_id)

        device.send([0x01, 0x02])

        # Check call
        coord.send_message.assert_called_with(ext_id, [0x01, 0x02], is_extended_id=True)

    def test_send_extended_id_inferred(self):
        coord = MagicMock(spec=CanCoordinator)
        # Extended ID > 0x7FF
        ext_id = 0x12345678

        # Initialize without flag (inference)
        device = CanDevice(coord, ext_id)

        self.assertTrue(device.is_extended_id)

        device.send([0x01, 0x02])

        # Check call
        coord.send_message.assert_called_with(ext_id, [0x01, 0x02], is_extended_id=True)

if __name__ == "__main__":
    unittest.main()
