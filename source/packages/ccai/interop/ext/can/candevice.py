"""
    CAN Device implementation.
"""
from typing import List, Union, Optional
from ccai.interop.ext.can.cancoordinator import CanCoordinator

class CanDevice:
    """
    Represents a device on the CAN bus.
    """
    def __init__(self, coordinator: CanCoordinator, arbitration_id: int, is_extended_id: Optional[bool] = None):
        """
        Initializes the CAN Device.

        :param coordinator: The CAN Coordinator instance.
        :param arbitration_id: The arbitration ID of the device (or the ID used to talk to it).
        :param is_extended_id: Whether the ID is an extended ID. If None, it is inferred from arbitration_id > 0x7FF.
        """
        self._coordinator = coordinator
        self._arbitration_id = arbitration_id
        if is_extended_id is None:
            self._is_extended_id = arbitration_id > 0x7FF
        else:
            self._is_extended_id = is_extended_id

    @property
    def arbitration_id(self) -> int:
        """Returns the arbitration ID."""
        return self._arbitration_id

    @property
    def is_extended_id(self) -> bool:
        """Returns whether the ID is extended."""
        return self._is_extended_id

    def send(self, data: Union[List[int], bytes]):
        """
        Sends data to this device.

        :param data: The data payload.
        """
        self._coordinator.send_message(self._arbitration_id, data, is_extended_id=self._is_extended_id)

    def __repr__(self):
        return f"CanDevice(id={hex(self._arbitration_id)}, ext={self._is_extended_id})"
