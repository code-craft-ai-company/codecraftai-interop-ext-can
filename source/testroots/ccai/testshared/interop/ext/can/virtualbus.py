"""
    .. module:: virtualbus
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: An in-process CAN bus for tests, built on python-can's ``virtual`` interface.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []

from typing import List, Optional, Union

import threading
import uuid

import can

from ccai.interop.ext.can.cancoordinator import CanCoordinator
from ccai.interop.ext.can.canpresence import CanPresence


# python-can's 'virtual' interface delivers a frame to every other bus opened
# on the same channel name, in-process, without any adapter.  This is the name
# the coordinator passes to python-can when it connects.
VIRTUAL_INTERFACE = "virtual"

# The presence monitor names its background thread; the fixture joins threads
# by that name because CanPresence.stop() does not join them itself.
PRESENCE_MONITOR_THREAD_NAME = "am-can-presence-mon"

# In-process delivery is immediate, so these only bound how long a broken test
# can hang, they do not pace a passing one.
DEFAULT_PEER_RECV_TIMEOUT = 2.0
DEFAULT_THREAD_JOIN_TIMEOUT = 5.0


def join_presence_monitor_threads(timeout: float = DEFAULT_THREAD_JOIN_TIMEOUT) -> int:
    """
        Waits for every live presence monitor thread to exit.

        :param timeout: The time in seconds to wait on each thread.

        :returns: The number of monitor threads that were still alive after the wait.
    """
    remaining = 0

    for thread in threading.enumerate():
        if thread.name == PRESENCE_MONITOR_THREAD_NAME:
            thread.join(timeout=timeout)
            if thread.is_alive():
                remaining += 1

    return remaining


def count_presence_monitor_threads() -> int:
    """
        Counts the presence monitor threads that are currently alive.

        :returns: The number of live threads named after the presence monitor.
    """
    count = 0

    for thread in threading.enumerate():
        if thread.name == PRESENCE_MONITOR_THREAD_NAME:
            count += 1

    return count


class VirtualCanBus:
    """
        A :class:`VirtualCanBus` stands in for a CAN adapter and the other devices on its
        wire.  It owns a channel with a name unique to the instance, so tests never see
        each other's traffic, and a 'peer' bus on that channel that plays the part of the
        remote devices: frames the product sends arrive at the peer, and frames sent from
        the peer arrive at whatever the product connected.

        Use it as a context manager.  On exit it stops the presences it created, waits for
        their monitor threads, disconnects the coordinators it created and shuts the peer
        down, in that order, so no monitor loop polls a closed bus.
    """

    def __init__(self, bitrate: int = 500000):
        """
            :param bitrate: The bitrate handed to the coordinators this bus creates.  The
                            virtual interface accepts and ignores it.
        """
        self._channel = "ccai-can-test-{}".format(uuid.uuid4().hex)
        self._bitrate = bitrate
        self._peer: Optional[can.BusABC] = None
        self._coordinators: List[CanCoordinator] = []
        self._presences: List[CanPresence] = []
        return

    def __enter__(self) -> "VirtualCanBus":
        self._peer = can.Bus(channel=self._channel, interface=VIRTUAL_INTERFACE)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    @property
    def bitrate(self) -> int:
        """
            The bitrate handed to coordinators created by this bus.
        """
        return self._bitrate

    @property
    def channel(self) -> str:
        """
            The unique virtual channel name shared by the peer and every coordinator
            created by this bus.
        """
        return self._channel

    @property
    def peer(self) -> can.BusABC:
        """
            The bus that represents the other devices on the wire.

            :raises: RuntimeError
        """
        if self._peer is None:
            raise RuntimeError("The VirtualCanBus must be entered before its peer is used.")

        return self._peer

    def close(self) -> None:
        """
            Releases everything this bus created.  Safe to call more than once.
        """
        for presence in self._presences:
            presence.stop()

        self._presences = []

        join_presence_monitor_threads()

        for coordinator in self._coordinators:
            coordinator.disconnect()

        self._coordinators = []

        if self._peer is not None:
            self._peer.shutdown()
            self._peer = None

        return

    def create_coordinator(self, connect: bool = True) -> CanCoordinator:
        """
            Creates a :class:`CanCoordinator` on this bus's channel using the virtual
            interface, the same way product code would with a real adapter.

            :param connect: When ``True`` the coordinator is connected before it is returned.

            :returns: The coordinator.  It is disconnected when the bus closes.
        """
        coordinator = CanCoordinator(channel=self._channel, bustype=VIRTUAL_INTERFACE, bitrate=self._bitrate)

        if connect:
            coordinator.connect()

        self._coordinators.append(coordinator)

        return coordinator

    def create_presence(self, coordinator: Optional[CanCoordinator] = None, start: bool = True) -> CanPresence:
        """
            Creates a :class:`CanPresence` over a coordinator on this bus.

            :param coordinator: The coordinator to monitor.  When ``None`` a connected one is created.
            :param start: When ``True`` the presence monitor is started before it is returned.

            :returns: The presence.  It is stopped, and its thread joined, when the bus closes.
        """
        if coordinator is None:
            coordinator = self.create_coordinator(connect=True)

        presence = CanPresence(coordinator)

        if start:
            presence.start()

        self._presences.append(presence)

        return presence

    def send_from_peer(self, arbitration_id: int, data: Optional[Union[List[int], bytes]] = None,
                       is_extended_id: bool = False) -> can.Message:
        """
            Sends a frame from the peer, as a remote device would.

            :param arbitration_id: The arbitration id of the frame.
            :param data: The payload.  ``None`` sends an empty payload.
            :param is_extended_id: Whether the frame carries a 29-bit id.

            :returns: The message that was sent.
        """
        if data is None:
            data = []

        message = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=is_extended_id)

        peer = self.peer
        peer.send(message)

        return message

    def recv_on_peer(self, timeout: float = DEFAULT_PEER_RECV_TIMEOUT) -> Optional[can.Message]:
        """
            Receives the next frame that reached the peer.

            :param timeout: The time in seconds to wait for a frame.

            :returns: The frame, or ``None`` when nothing arrived within the timeout.
        """
        peer = self.peer

        message = peer.recv(timeout)

        return message
