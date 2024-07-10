:fa:`server` Build Backend Plugin
*********************************

You can even use this plugin without PDM. This is enabled by build backend hooks.

Currently, both `pdm-backend <https://backend.pdm-project.org>`__ and `hatchling <https://hatch.pypa.io>`__ are supported.

To set it up, a few configuration steps are required.

Lockfile configuration
======================

Your lockfile must be configured with the ``include_metadata`` strategy (``pdm>=2.11``) and include locks for the
optional-dependencies groups you want to publish locked.

buildsystem configuration
=========================

This step depends on the build-system you use and requires you to add the following to your ``pyproject.toml``.

pdm-backend
~~~~~~~~~~~

.. code-block:: toml
    :caption: pyproject.toml

    [build-system]
    requires = ["pdm-backend", "pdm-build-locked"]
    build-backend = "pdm.backend"

    [tool.pdm.build]
    locked = true

hatchling
~~~~~~~~~

.. code-block:: toml
    :caption: pyproject.toml

    [build-system]
    requires = ["hatchling", "pdm-build-locked"]
    build-backend = "hatchling.build"

    [tool.hatch.metadata.hooks.build-locked]


Select groups to lock
~~~~~~~~~~~~~~~~~~~~~

By default, the default group and all optional groups will be locked, but you can specify the groups to lock by setting `locked-groups` in the configuration.

.. code-block:: toml
    :caption: pyproject.toml
    # for pdm-backend
    [tool.pdm.build]
    locked = true
    locked-groups = ["default", "optional1"]

    # for hatchling
    [tool.hatch.metadata.hooks.build-locked]
    locked-groups = ["default", "optional1"]
