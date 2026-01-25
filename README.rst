==================================================================
Automation Mojo 'CAN' Interop Extension - automojo-interop-ext-can
==================================================================
The Automation Mojo CAN interop extension provides Python tooling meant for
test frameworks and automation workflows that integrate with CAN-based systems.
This repository follows the Automation Mojo standards for readability,
debuggability, and consistent test organization.

========
Overview
========
* Python package project managed by Poetry.
* Source code lives in ``source/packages``.
* Tests live in ``source/testroots`` and mirror the source hierarchy.
* Repository standards are documented in the ``userguide`` directory.

==================
Getting Started
==================
1. Run the repository setup script to create the local ``.env`` file::

     repository-setup/rehome-repository

2. Create the virtual environment::

     development/setup-envrionment

3. Install dependencies (if not handled by the setup scripts)::

     poetry install

=====================
Development Workflow
=====================
* Add package code under ``source/packages``.
* Add tests under ``source/testroots`` with a matching package hierarchy.
* Favor clarity and debugging support over micro-optimizations.

===================
Testing Frameworks
===================
This repository supports multiple test frameworks. Refer to the user guide
for details on when and how to use each framework:

* ``unittest``
* ``pytest``
* ``testbase``

=============
References
=============
* `User Guide <userguide/userguide.rst>`_
* `Coding Standards <userguide/10-00-coding-standards.rst>`_
* `Code Organization <userguide/10-01-code-organization.rst>`_
* `Naming Conventions <userguide/10-02-naming-conventions.rst>`_
