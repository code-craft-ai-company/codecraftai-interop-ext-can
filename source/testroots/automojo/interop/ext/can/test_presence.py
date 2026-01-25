import unittest
from unittest.mock import MagicMock
import can
from automojo.interop.ext.can.coordinator import CanCoordinator
from automojo.interop.ext.can.presence import CanPresence

class TestCanPresence(unittest.TestCase):

    def test_scan(self):
        mock_coord = MagicMock(spec=CanCoordinator)

        msg1 = can.Message(arbitration_id=0x100)
        msg2 = can.Message(arbitration_id=0x200)
        msg3 = can.Message(arbitration_id=0x100) # Duplicate

        msgs = [msg1, msg2, msg3]

        def side_effect(*args, **kwargs):
            if msgs:
                return msgs.pop(0)
            return None

        mock_coord.receive_message.side_effect = side_effect

        presence = CanPresence(mock_coord)

        # Short scan time for test
        detected = presence.scan(duration=0.1)

        self.assertEqual(detected, [0x100, 0x200])
        self.assertTrue(mock_coord.receive_message.called)
