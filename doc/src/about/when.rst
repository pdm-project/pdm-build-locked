:fa:`star` When to use
**********************

To avoid misuse, we recommend deciding whether to use this plugin based on your project type:

- :fa:`check-circle` **CLI tool**: If your package is a CLI tool that will be installed in an isolated virtualenv, for example using ``pipx``.
- :fa:`check-circle` **CLI tool and library**: Recommended. Advise your users to only use the [locked] group when used as an executable (never in ``pyproject.toml`` dependencies!).
- :fa:`times-circle` **Library only**: Do not use.

.. danger::

    The following example is highly discouraged and should never be used, as it will easily lead to dependency conflicts.

    ``pyproject.toml``

    .. code-block::

        dependencies = [
            my-library[locked]==1.1.1,  # this will break your install sooner rather than later
            some-other-library
        ]
