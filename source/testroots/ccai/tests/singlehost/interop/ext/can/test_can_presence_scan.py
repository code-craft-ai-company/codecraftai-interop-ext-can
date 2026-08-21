from ccai import testbase

from unittest.mock import MagicMock
import can
from ccai.interop.ext.can.cancoordinator import CanCoordinator
from ccai.interop.ext.can.canpresence import CanPresence

# ----------------------------------------------------------------------
# TestCanPresence
# ----------------------------------------------------------------------


def test_scan() -> None:
    """
        A repeated arbitration id collapses to a single discovered device.

        The window was 0.1s, which is not long enough for the monitor
        thread to drain the mocked messages before it closes -- the test
        could never have passed, and it never ran, because this module sat
        at a path that shadowed the product package. It uses the same 2.0s
        window as test_can_presence_discovery now.
    """
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

    # The monitor thread starts with presence.start(), before the search
    # window is open.  Priming the messages first lets that thread drain
    # them while nothing is recording, so deliver them only once the
    # window exists -- the same ordering test_can_presence_discovery uses.
    mock_coord.receive_message.side_effect = lambda timeout=1.0: None

    presence = CanPresence(mock_coord)
    presence.start()

    try:
        window = presence.discover_devices(window_length=2.0, monitor_interval=0.01)
        mock_coord.receive_message.side_effect = receive_side_effect
        window.wait()

        detected = sorted(list(window.devices_found.keys()))
        testbase.assert_equal(detected, [0x100, 0x200])
    finally:
        presence.stop()

    testbase.assert_true(mock_coord.receive_message.called)
