
import time
from unittest.mock import MagicMock, Mock

from ccai.interop.ext.can.canpresence import CanPresence

def test_can_presence_discovery():
    """
    Verify that CanPresence can discover devices using windowed search and mocked coordinator.
    """
    
    # Mock Coordinator
    mock_coordinator = MagicMock()
    
    # Instantiate Presence
    presence = CanPresence(mock_coordinator)
    
    try:
        presence.start()
        
        # Start Discovery
        window = presence.discover_devices(window_length=2.0)
        
        # Simulate CAN messages arriving over time
        # Since the loop pulls safely from coordinator, we can setup side effects
        
        current_time = time.time()
        
        # Create a Mock Message object
        msg1 = Mock()
        msg1.arbitration_id = 0x123
        msg1.data = b'\x01\x02'
        msg1.is_extended_id = False
        msg1.timestamp = current_time
        
        msg2 = Mock()
        msg2.arbitration_id = 0x456
        msg2.data = b'\x03\x04'
        msg2.is_extended_id = False
        msg2.timestamp = current_time + 0.1

        # Setup side_effect to return messages then None (timeout in real life, or just silence)
        # The loop calls receive_message(timeout=0.1)
        # We need it to return msg1, then msg2, then maybe None equivalent to keep loop running empty
        
        mock_coordinator.receive_message.side_effect = [msg1, msg2, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None] 
        
        # Wait for window processing
        time.sleep(1.0)
        
        found = window.devices_found
        
        # Assertions
        if 0x123 not in found:
            raise AssertionError("Device 0x123 not found in search window results")
        
        if 0x456 not in found:
            raise AssertionError("Device 0x456 not found in search window results")
            
        dev1 = found[0x123]
        if dev1.data != b'\x01\x02':
             raise AssertionError(f"Device 0x123 data mismatch. Got {dev1.data}")
             
        # Wait for window completion
        window.wait(timeout=3.0)
        
        if window.is_active():
            raise AssertionError("Search window did not close after timeout")

    finally:
        presence.stop()
