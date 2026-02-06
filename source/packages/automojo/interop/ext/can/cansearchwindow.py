
"""
    .. module:: cansearchwindow
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: cansearchwindow module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Dict, List, Optional, TYPE_CHECKING
import threading
import time
import weakref
from datetime import datetime
from .candeviceevidence import CanDeviceEvidence

if TYPE_CHECKING:
    from automojo.interop.ext.can.canpresence import CanPresence


class CanSearchWindowState:
    """
        Enumeration describing the lifecycle of a CAN search window.
    """
    INACTIVE = 0
    ACTIVE = 1
    COMPLETED = 2
    TIMEOUT = 3


class CanSearchWindow:
    """
        The CanSearchWindow class provides a synchronization and state managment device for synchronizing the state of CAN search
        activities.
    """

    def __init__(self, presence: "CanPresence", id: str, start: datetime, end: datetime, monitor_interval: float, limit_to: List[int]=None):
        """
            :param presence: The owning :class:`CanPresence` instance.
            :param id: Identifier for this search window.
            :param start: Start time of the search window.
            :param end: End time of the search window.
            :param monitor_interval: Polling interval for window monitoring.
            :param limit_to: Optional list of arbitration IDs to limit the search.
        """

        self._presence_ref = weakref.ref(presence)
        self._id = id
        self._start = start
        self._end = end
        self._monitor_interval = monitor_interval
        self._limit_to = limit_to

        self._still_waiting_for = None
        if limit_to is not None:
            self._still_waiting_for = [hint for hint in limit_to]

        self._window_state = CanSearchWindowState.INACTIVE

        self._lock = threading.Lock()
        self._wait_gate = threading.Event()
        self._monitor_thread = None

        self._devices_found = {} # Map ID (int) -> CanDeviceEvidence
        self._matching_devices = {}
        
        return

    @property
    def devices_found(self) -> Dict[int, CanDeviceEvidence]:
        """
            The dictionary of devices found during the search window.
            :returns: Copy of the devices found mapping.
        """
        with self._lock:
            rtnval = self._devices_found.copy()
        return rtnval

    @property
    def id(self) -> str:
        """
            The ID of the search window.
        """
        return self._id
    
    @property
    def matching_devices(self) -> Dict[int, CanDeviceEvidence]:
        """
            The dictionary of devices that matched the search window criteria.
        """
        with self._lock:
            rtnval = self._matching_devices.copy()
        return rtnval

    @property
    def presence(self) -> Optional["CanPresence"]:
        """
            The :class:`CanPresence` object that is associated with this search window.
            Returns None if the presence object has been garbage collected.
        """
        return self._presence_ref()


    def add_evidence(self, evidence: CanDeviceEvidence):
        """
            Add evidence to the list of devices found during the search window.
        """

        with self._lock:
            self._devices_found[evidence.arbitration_id] = evidence

        return


    def is_active(self) -> bool:
        """
            Check if the search window is active.
        """

        with self._lock:
            return self._window_state == CanSearchWindowState.ACTIVE


    def start(self):
        """
            Begin monitoring for search results in a background thread.
        """
        self._lock.acquire()
        try:
            start_gate = threading.Event()
            start_gate.clear()

            self._monitor_thread = threading.Thread(target=self._monitor_thread_entry, name="am-can-search-window-mon", args=(start_gate,), daemon=True)
            self._monitor_thread.start()
        finally:
            self._lock.release()

        start_gate.wait()

        return


    def wait(self, timeout: float = None) -> bool:
        """
            Wait for the search window to close.

            :param timeout: The time in seconds to wait for the search window to close.  If None, then wait indefinitely.

            :returns: ``True`` if the window closed before timeout, otherwise ``False``.
        """

        # Check initial state
        with self._lock:
            if self._window_state == CanSearchWindowState.INACTIVE:
                raise RuntimeError("The search window is not active.")
            
            if self._window_state != CanSearchWindowState.ACTIVE:
                # Window is already completed or timed out
                return True

        # Wait for completion without holding the lock
        completed_successfully = self._wait_gate.wait(timeout=timeout)

        return completed_successfully


    def _monitor_thread_entry(self, sgate: threading.Event):
        """
            The monitor thread entry point.
        """

        with self._lock:
            self._window_state = CanSearchWindowState.ACTIVE
            self._wait_gate.clear()

        sgate.set()

        while True:
            with self._lock:
                if self._window_state != CanSearchWindowState.ACTIVE:
                    break
            
            now = datetime.now()

            if now > self._end:
                with self._lock:
                    self._window_state = CanSearchWindowState.TIMEOUT
                break

            # Get current state atomically
            with self._lock:
                if self._still_waiting_for is not None:
                    checking_for = [hint for hint in self._still_waiting_for]
                    current_found = self._devices_found.copy()
                else:
                    checking_for = None
                    current_found = {}

            # Process hints
            if checking_for is not None:
                matched_hints = []
                matched_devices = {}
                
                for nxt_id_hint in checking_for:
                    if nxt_id_hint in current_found:
                         matched_hints.append(nxt_id_hint)
                         matched_devices[nxt_id_hint] = current_found[nxt_id_hint]

                # Update shared state atomically
                with self._lock:
                    if self._still_waiting_for is not None:
                        for matched_hint in matched_hints:
                            if matched_hint in self._still_waiting_for:
                                self._still_waiting_for.remove(matched_hint)
                    
                    self._matching_devices.update(matched_devices)

                    if self._still_waiting_for is not None and len(self._still_waiting_for) == 0:
                        self._window_state = CanSearchWindowState.COMPLETED
                        break

            time.sleep(self._monitor_interval)

        self._wait_gate.set()
        
        return
