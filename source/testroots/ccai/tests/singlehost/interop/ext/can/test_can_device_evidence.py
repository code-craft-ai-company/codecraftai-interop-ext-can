"""
    Tests for :class:`CanDeviceEvidence`.
"""

from datetime import datetime

from ccai import testbase

from ccai.interop.ext.can.candeviceevidence import CanDeviceEvidence


def test_properties_reflect_constructor() -> None:
    """
        Every constructor argument is exposed unchanged.
    """
    when = datetime(2025, 1, 2, 3, 4, 5)

    evidence = CanDeviceEvidence(0x12345678, timestamp=when, data=b"\x01\x02", is_extended_id=True)

    testbase.assert_equal(evidence.arbitration_id, 0x12345678)
    testbase.assert_equal(evidence.timestamp, when)
    testbase.assert_equal(evidence.data, b"\x01\x02")
    testbase.assert_true(evidence.is_extended_id)

    return


def test_default_timestamp_is_now() -> None:
    """
        Without a timestamp the evidence is stamped with the time of creation.
    """
    before = datetime.now()

    evidence = CanDeviceEvidence(0x123)

    after = datetime.now()
    testbase.assert_true(before <= evidence.timestamp)
    testbase.assert_true(evidence.timestamp <= after)

    return


def test_default_flags_are_standard_frame_without_data() -> None:
    """
        By default the evidence describes a standard frame with no payload.
    """
    evidence = CanDeviceEvidence(0x123)

    testbase.assert_true(evidence.data is None)
    testbase.assert_false(evidence.is_extended_id)

    return


def test_as_dict_with_data() -> None:
    """
        The dictionary form carries the id, an ISO timestamp, the payload as hex and the flag.
    """
    when = datetime(2025, 1, 2, 3, 4, 5)
    evidence = CanDeviceEvidence(0x123, timestamp=when, data=b"\xde\xad", is_extended_id=False)

    as_dict = evidence.as_dict()

    expected = {
        "arbitration_id": 0x123,
        "timestamp": "2025-01-02T03:04:05",
        "data": "dead",
        "is_extended_id": False,
    }
    testbase.assert_equal(as_dict, expected)

    return


def test_as_dict_without_data() -> None:
    """
        Missing payload is reported as None rather than an empty string.
    """
    when = datetime(2025, 1, 2, 3, 4, 5)
    evidence = CanDeviceEvidence(0x123, timestamp=when)

    as_dict = evidence.as_dict()

    testbase.assert_true(as_dict["data"] is None)

    return


def test_str_names_id_and_flag() -> None:
    """
        The string form shows the id in hex and the extended flag.
    """
    evidence = CanDeviceEvidence(0x123, is_extended_id=True)

    testbase.assert_equal(str(evidence), "<CanDeviceEvidence id=0x123 ext=True>")

    return
