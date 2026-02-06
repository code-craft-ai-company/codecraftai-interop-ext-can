"""
    CAN Device implementation.
"""
from typing import List, Union
from .cancoordinator import CanCoordinator

class CanDevice:
    """
    Represents a device on the CAN bus.
    """
    def __init__(self, coordinator: CanCoordinator, arbitration_id: int):
        """
        Initializes the CAN Device.

        :param coordinator: The CAN Coordinator instance.
        :param arbitration_id: The arbitration ID of the device (or the ID used to talk to it).
        """
        self._coordinator = coordinator
        self._arbitration_id = arbitration_id

    @property
    def arbitration_id(self) -> int:
        """Returns the arbitration ID."""
        return self._arbitration_id

    def send(self, data: Union[List[int], bytes]):
        """
        Sends data to this device.

        :param data: The data payload.
        """
        self._coordinator.send_message(self._arbitration_id, data)

    def __repr__(self):
        return f"CanDevice(id={hex(self._arbitration_id)})"
