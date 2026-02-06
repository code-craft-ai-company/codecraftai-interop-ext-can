
"""
    .. module:: candeviceevidence
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the CanDeviceEvidence object.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict, List, Optional, Any
from datetime import datetime

class CanDeviceEvidence:
    """
        A :class:`CanDeviceEvidence` object is used to track evidence of the current state of CAN devices.
    """

    def __init__(self, arbitration_id: int, timestamp: Optional[datetime] = None, 
                 data: Optional[bytes] = None, is_extended_id: bool = False):
        """
            Initialize evidence.
        """
        self._arbitration_id = arbitration_id
        self._timestamp = timestamp if timestamp else datetime.now()
        self._data = data
        self._is_extended_id = is_extended_id

    @property
    def arbitration_id(self) -> int:
        return self._arbitration_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp
        
    @property
    def data(self) -> Optional[bytes]:
        return self._data
        
    @property
    def is_extended_id(self) -> bool:
        return self._is_extended_id
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "arbitration_id": self._arbitration_id,
            "timestamp": self._timestamp.isoformat(),
            "data": self._data.hex() if self._data else None,
            "is_extended_id": self._is_extended_id
        }

    def __str__(self):
        return f"<CanDeviceEvidence id={hex(self._arbitration_id)} ext={self._is_extended_id}>"
