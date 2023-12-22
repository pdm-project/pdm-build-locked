:fa:`lightbulb-o` What it does
******************************

Normally, you would only be able to use your locked dependencies from your lockfile when using pdm in your dev environment.

This plugin enables using the lockfile in a **deployment scenario**.

Thus, your users may install your package as an exact reproduction of your dev environment lockfile by running:

``pip install mypkg[locked]``

So for ``mypkg`` with ``optional-dependencies`` group ``extras`` you will end up with the following groups:

- ``locked``
- ``extras-locked``

To install both, you would run:

``pip install mypkg[locked, extras-locked]``


.. hint::

      It achieves this by adding optional-dependencies groups that allow the user to opt-in to installing the dependencies that were pinned in the lockfile:

      - ``[locked]`` - contains all default dependencies as pinned version from lockfile
      - for each optional-dependencies group ``<group>``:

          - ``[<group>-locked]`` - contains optional dependencies for group <group> as pinned version from lockfile
