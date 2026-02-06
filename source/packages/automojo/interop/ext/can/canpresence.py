
"""
    CAN Presence implementation.
"""
import logging
import time
import threading
import uuid
import weakref
from typing import List, Set, Dict, Optional
from datetime import datetime, timedelta

from .cancoordinator import CanCoordinator
from .cansearchwindow import CanSearchWindow
from .candeviceevidence import CanDeviceEvidence

class CanPresence:
    """
    Handles presence detection on the CAN bus using a background monitoring thread.
    """
    def __init__(self, coordinator: CanCoordinator):
        """
        Initializes the CAN Presence detector.

        :param coordinator: The CAN Coordinator instance.
        """
        self._coordinator = coordinator
        self._logger = logging.getLogger(__name__)

        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread = None
        
        self._detected_ids: Set[int] = set()
        self._active_devices: Dict[int, CanDeviceEvidence] = {}
        
        self._search_windows: Dict[str, weakref.ref] = {}


    def start(self):
        """
        Starts the CAN bus monitoring thread.
        """
        with self._lock:
            if self._running:
                return
            
            self._running = True
            
            # Start background thread
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="am-can-presence-mon")
            self._monitor_thread.start()
            
            self._logger.info("CAN Presence monitoring started.")

    def stop(self):
        """
        Stops the CAN bus monitoring thread.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False
            
        # Join thread? Or just let it die as daemon?
        # Ideally join but we won't block here.
        self._logger.info("CAN Presence monitoring stopped.")

    def discover_devices(self, limit_to: List[int]=None, window_length: float = 2.0,
                         monitor_interval: float = 0.5) -> CanSearchWindow:
        """
        Opens a search window for devices.
        Returns a CanSearchWindow.
        """
        if not self._running:
             raise RuntimeError("CanPresence must be running. Call start().")

        start = datetime.now()
        end = start + timedelta(seconds=window_length)
        wid = str(uuid.uuid4())

        window = CanSearchWindow(self, wid, start, end, monitor_interval, limit_to=limit_to)
        
        with self._lock:
            self._search_windows[wid] = weakref.ref(window)
        
        window.start()
        return window

    def _monitor_loop(self):
        """
        Background loop to read CAN messages.
        """
        while True:
            with self._lock:
                if not self._running:
                    break
            
            # Read message with short timeout
            try:
                msg = self._coordinator.receive_message(timeout=0.1)
                
                if msg:
                    timestamp = getattr(msg, 'timestamp', None)
                    if timestamp:
                        timestamp = datetime.fromtimestamp(timestamp)
                    else:
                        timestamp = datetime.now()
                    
                    arbitration_id = msg.arbitration_id
                    data = getattr(msg, 'data', None)
                    is_extended = getattr(msg, 'is_extended_id', False)
                    
                    evidence = CanDeviceEvidence(arbitration_id, timestamp, data, is_extended)
                    
                    with self._lock:
                        self._detected_ids.add(arbitration_id)
                        self._active_devices[arbitration_id] = evidence
                        
                        # Notify windows
                        to_remove = []
                        for wid, wref in self._search_windows.items():
                            window = wref()
                            if window:
                                if window.is_active():
                                    window.add_evidence(evidence)
                            else:
                                to_remove.append(wid)
                        
                        for wid in to_remove:
                            del self._search_windows[wid]
                            
            except Exception as e:
                self._logger.error(f"Error in CAN monitor loop: {e}")
                time.sleep(1) # Prevent tight loop on repeated error
                
        return
