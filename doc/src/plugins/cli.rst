:fa:`terminal` PDM CLI plugin
*****************************

The PDM CLI plugin replaces the ``pdm build`` command with a locked build. Essentially it

- edits your ``pyproject.toml`` and adds the additional optional-dependency groups with pins from the lockfile to it
- hides the file changes from git to avoid a dirty status on build
- calls the actual ``pdm build`` command
- restores the original ``pyproject.toml``

The result is a wheel that is installable reproducibly, as it contains the exact dependencies you used to build it.

It only requires the user to add ``[locked]`` on install.

Installing the plugin
=====================

To install the plugin, you need to run ``pdm install --plugins``.

Alternatively, you can activate the plugin globally by running ``pdm self add pdm-build-locked``.


Plugin registration
===================

``pyproject.toml``

.. code-block::

    [tool.pdm]
    plugins = [
        "pdm-build-locked"
    ]

This registers the plugin with pdm.


Enabling the plugin
===================

To enable locked builds, set the ``locked`` entry in ``pyproject.toml``:

    .. code-block::

        [tool.pdm.build]
        package-dir = "src"
        locked = true

    This will enable locked releases in the pipeline, as it also affects a basic ``pdm build`` call.


.. hint::

    Locally, the following options also work.

    - run ``pdm build --locked``
    - set ``PDM_BUILD_LOCKED`` env var to ``true``
