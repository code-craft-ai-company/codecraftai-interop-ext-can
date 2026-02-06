"""
    CAN Coordinator implementation.
"""
import logging
from typing import Optional, List, Union

import can

class CanCoordinator:
    """
    Coordinator for CAN bus interactions.
    """
    def __init__(self, channel: str, bustype: str = 'virtual', bitrate: int = 500000):
        """
        Initializes the CAN Coordinator.

        :param channel: The CAN interface name (e.g., 'can0', 'vcan0').
        :param bustype: The type of bus (e.g., 'socketcan', 'virtual').
        :param bitrate: The bitrate of the CAN bus.
        """
        self._channel = channel
        self._bustype = bustype
        self._bitrate = bitrate
        self._bus: Optional[can.BusABC] = None
        self._logger = logging.getLogger(__name__)

    def connect(self):
        """
        Connects to the CAN bus.

        :raises: can.CanError
        """
        self._logger.info(f"Connecting to CAN bus {self._channel} ({self._bustype})")
        try:
            self._bus = can.Bus(channel=self._channel, bustype=self._bustype, bitrate=self._bitrate)
            self._logger.info("Connected to CAN bus")
        except Exception as e:
            self._logger.error(f"Failed to connect to CAN bus: {e}")
            raise

    def disconnect(self):
        """
        Disconnects from the CAN bus.
        """
        if self._bus:
            self._bus.shutdown()
            self._bus = None
            self._logger.info("Disconnected from CAN bus")

    def send_message(self, arbitration_id: int, data: Union[List[int], bytes], is_extended_id: bool = False):
        """
        Sends a message on the CAN bus.

        :param arbitration_id: The ID of the message.
        :param data: The data payload.
        :param is_extended_id: Whether to use extended ID.
        :raises: RuntimeError, can.CanError
        """
        if not self._bus:
            raise RuntimeError("Not connected to CAN bus")

        msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=is_extended_id)
        try:
            self._bus.send(msg)
            self._logger.debug(f"Sent message: {msg}")
        except can.CanError as e:
            self._logger.error(f"Failed to send message: {e}")
            raise

    def receive_message(self, timeout: float = 1.0) -> Optional[can.Message]:
        """
        Receives a message from the CAN bus.

        :param timeout: Time to wait for a message in seconds.
        :return: The received message or None if timeout.
        :raises: RuntimeError
        """
        if not self._bus:
            raise RuntimeError("Not connected to CAN bus")

        return self._bus.recv(timeout)
