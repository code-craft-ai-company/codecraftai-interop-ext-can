import unittest
from unittest.mock import MagicMock
from automojo.interop.ext.can.coordinator import CanCoordinator
from automojo.interop.ext.can.device import CanDevice

class TestCanDevice(unittest.TestCase):
    def test_send(self):
        coord = MagicMock(spec=CanCoordinator)
        device = CanDevice(coord, 0x123)

        device.send([1, 2, 3])

        coord.send_message.assert_called_with(0x123, [1, 2, 3])
