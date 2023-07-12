Instructions
############

When to use
************

This package is opt-in for both developers and users.

- For developers, it requires enabling the plugin by adding ``locked==true``
- For users, it requires users to explicitly specify the optional dependency group ``[locked]`` on install.

To avoid misuse, we recommend deciding whether to use this plugin based on your project type:

- **CLI tool**: If your package is a CLI tool that will be installed in an isolated virtualenv, for example using ``pipx``.
- **CLI tool and library**: Recommended. Advise your users to only use the [locked] group when used as an executable (never in pyproject.toml!).
- **Library only**: Do not use.

.. danger::

    The following example is highly discouraged and should never be used, as it will easily lead to dependency conflicts.

    ``pyproject.toml``

    .. code-block::

        dependencies = [
            my-library[locked]==1.1.1,  # this will break your install sooner rather than later
            some-other-library
        ]

Usage
*****

This plugin must be installed *and* activated explicitly.

Installation
==================

``pyproject.toml``

.. code-block::

    [tool.pdm]
    plugins = [
        "pdm-build-locked"
    ]

This registers the plugin with pdm.

.. hint::

    To install the plugin locally, you need to run ``pdm install --plugins``.
    This is only needed if you want to test the locking. On CI, plugins will be installed in the release job.

Activate the plugin
*******************

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
