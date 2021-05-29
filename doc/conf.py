# Configuration file for the Sphinx documentation builder.

# -- Mark as Sphinx build ----------------------------------------------------

import builtins
builtins.__sphinx_build__ = True

# -- Path setup --------------------------------------------------------------

import os
import sys
# Add Plover base directory so we can import plover below
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

from plover import __name__ as __software_name__, __version__, __copyright__

project = __software_name__.capitalize()
copyright = "2020 " + __copyright__.replace("(C) ", "")
author = copyright

release = __version__
version = release

# -- General configuration ---------------------------------------------------

import sphinx_rtd_theme

extensions = [
  'sphinx_rtd_theme',
  'sphinxcontrib.yt',
  'sphinx.ext.autodoc',
  'sphinx.ext.napoleon',
  'sphinx.ext.autosectionlabel',
]

templates_path = ['_templates']

exclude_patterns = []

autodoc_mock_imports = []

# -- Options for Sphinx autodoc ----------------------------------------------

autodoc_typehints = "description"
autodoc_type_aliases = {
        "ConfigKey": "plover.config.ConfigKey",
        "ConfigFullKey": "plover.config.ConfigFullKey",
        "ConfigValue": "plover.config.ConfigValue",
        }
#autodoc_typehints = "both"  # does not work


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']

html_sidebars = {
  '**': [
    'globaltoc.html',
    'relations.html',
    'sourcelink.html',
    'searchbox.html',
  ],
}

# -- Napoleon settings -------------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True
