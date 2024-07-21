pdm-build-locked
################

pdm-build-locked is a pdm plugin to enabling reproducible installs of Python CLI tools -- no breakage on dependency updates.

It achieves this by adding the pinned packages from PDM's lockfile as additional optional dependency groups to the distribution metadata.

Compatible with ``pdm>=2.11``.


.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: About

   about/what
   about/when

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: Plugins

   plugins/choice
   plugins/cli
   plugins/backend

