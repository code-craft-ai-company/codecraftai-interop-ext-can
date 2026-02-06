import unittest
from unittest.mock import MagicMock
import can
from automojo.interop.ext.can.cancoordinator import CanCoordinator
from automojo.interop.ext.can.canpresence import CanPresence

class TestCanPresence(unittest.TestCase):

    def test_scan(self):
        mock_coord = MagicMock(spec=CanCoordinator)

        # Timestamps are needed for CanDeviceEvidence
        msg1 = can.Message(arbitration_id=0x100, timestamp=1000.0)
        msg2 = can.Message(arbitration_id=0x200, timestamp=1000.1)
        msg3 = can.Message(arbitration_id=0x100, timestamp=1000.2) # Duplicate

        msgs = [msg1, msg2, msg3]

        def receive_side_effect(timeout=1.0):
            if msgs:
                return msgs.pop(0)
            return None

        mock_coord.receive_message.side_effect = receive_side_effect

        presence = CanPresence(mock_coord)
        presence.start()

        try:
            # Short scan time for test
            window = presence.discover_devices(window_length=0.1, monitor_interval=0.01)
            window.wait()

            detected = sorted(list(window.devices_found.keys()))
            self.assertEqual(detected, [0x100, 0x200])
        finally:
            presence.stop()

        self.assertTrue(mock_coord.receive_message.called)

if __name__ == "__main__":
    unittest.main()
