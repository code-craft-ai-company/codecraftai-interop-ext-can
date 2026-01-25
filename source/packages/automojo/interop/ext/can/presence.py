"""
    CAN Presence implementation.
"""
import logging
import time
from typing import List, Set

from .coordinator import CanCoordinator

class CanPresence:
    """
    Handles presence detection on the CAN bus.
    """
    def __init__(self, coordinator: CanCoordinator):
        """
        Initializes the CAN Presence detector.

        :param coordinator: The CAN Coordinator instance.
        """
        self._coordinator = coordinator
        self._logger = logging.getLogger(__name__)
        self._detected_ids: Set[int] = set()

    def scan(self, duration: float = 2.0) -> List[int]:
        """
        Scans the CAN bus for active device IDs by listening to traffic.

        :param duration: How long to listen for messages in seconds.
        :return: A list of unique arbitration IDs detected.
        """
        self._logger.info(f"Scanning CAN bus for {duration} seconds...")
        self._detected_ids.clear()

        end_time = time.time() + duration

        while time.time() < end_time:
            remaining = end_time - time.time()
            if remaining <= 0:
                break

            # Using a small chunk for timeout to allow checking time condition frequently enough
            # but also relying on receive_message timeout
            msg = self._coordinator.receive_message(timeout=min(remaining, 0.1))
            if msg:
                self._detected_ids.add(msg.arbitration_id)

        self._logger.info(f"Scan complete. Detected {len(self._detected_ids)} devices.")
        return sorted(list(self._detected_ids))
