"""
    A floor on the number of tests the merge gate collects.

    The gate runs ``testbase testing run --root ./source/testroots/ccai
    --includes=ccai.tests.singlehost``.  If discovery regresses (an import error in a
    test module, a module moved outside the include prefix, a wrong ``--includes``),
    testbase quietly runs fewer tests and the gate stays green.  This test makes that
    loud: it collects the suite the way the runner does and fails when the count drops
    below the number reached by the test coverage roadmap.
"""

from typing import List

import os
import sys

from ccai import testbase

from ccai.testbase.testcollector import TestCollector
from ccai.testbase.utilities import find_testmodule_root


# The include expression the merge gate passes; see .github/workflows/merge_gate.yml.
GATE_INCLUDE_EXPRESSION = "ccai.tests.singlehost"

# The number of tests this suite had when the floor was set.  Raise it when tests are
# added; never lower it without removing tests on purpose.
EXPECTED_MINIMUM_TESTS = 67


def collect_gate_test_names() -> List[str]:
    """
        Collects the names of the tests the merge gate would run.

        The mechanism is the runner's own: a :class:`TestCollector` rooted at this test
        root (found by walking up to ``__testroot__.py`` exactly as the CLI does) is given
        the gate's include expression.  It walks the tree for matching modules, imports
        each one and records every ``test``-prefixed function as a reference.  Modules
        that fail to import are reported in ``import_errors`` rather than counted, which
        is the regression this floor exists to catch.

        :returns: The sorted, fully qualified test names.

        :raises: AssertionError
    """
    this_module = sys.modules[__name__]
    test_root = find_testmodule_root(this_module)

    collector = TestCollector(test_root, excludes=[], metafilters=[])
    collector.collect_references(GATE_INCLUDE_EXPRESSION)

    import_errors = collector.import_errors
    if len(import_errors) > 0:
        err_msg_lines = [
            "Test modules failed to import during collection:",
        ]
        for modname, ifile, errmsg in import_errors.values():
            err_msg_lines.append("    {} ({})".format(modname, ifile))
            err_msg_lines.append(errmsg)
        err_msg = os.linesep.join(err_msg_lines)
        raise AssertionError(err_msg)

    names = sorted(collector.references.keys())

    return names


def test_gate_collects_at_least_the_roadmap_count() -> None:
    """
        The gate's include expression selects at least ``EXPECTED_MINIMUM_TESTS`` tests.
    """
    names = collect_gate_test_names()

    collected = len(names)
    if collected < EXPECTED_MINIMUM_TESTS:
        err_msg_lines = [
            "The merge gate collects fewer tests than the floor.",
            "    include expression: {}".format(GATE_INCLUDE_EXPRESSION),
            "    expected at least: {}".format(EXPECTED_MINIMUM_TESTS),
            "    collected: {}".format(collected),
            "Collected tests:",
        ]
        for name in names:
            err_msg_lines.append("    {}".format(name))
        err_msg = os.linesep.join(err_msg_lines)
        raise AssertionError(err_msg)

    # The floor test itself must be among the collected tests, otherwise the
    # collector above is not looking at the same tree the gate runs.
    own_suffix = "#test_gate_collects_at_least_the_roadmap_count"
    found_self = False
    for name in names:
        if name.endswith(own_suffix):
            found_self = True
            break

    testbase.assert_true(found_self)

    return
