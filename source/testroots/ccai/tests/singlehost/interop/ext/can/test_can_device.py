
import unittest
from unittest.mock import MagicMock
from ccai.interop.ext.can.candevice import CanDevice
from ccai.interop.ext.can.cancoordinator import CanCoordinator

class TestCanDevice(unittest.TestCase):
    def test_init_and_properties(self):
        mock_coordinator = MagicMock(spec=CanCoordinator)
        arbitration_id = 0x123
        device = CanDevice(mock_coordinator, arbitration_id)

        self.assertEqual(device.arbitration_id, arbitration_id)
        self.assertEqual(str(device), f"CanDevice(id={hex(arbitration_id)})")

    def test_send(self):
        mock_coordinator = MagicMock(spec=CanCoordinator)
        arbitration_id = 0x456
        device = CanDevice(mock_coordinator, arbitration_id)

        data = [0x01, 0x02, 0x03]
        device.send(data)

        mock_coordinator.send_message.assert_called_once_with(arbitration_id, data)

if __name__ == '__main__':
    unittest.main()
