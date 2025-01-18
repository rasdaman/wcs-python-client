# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

import wcs.model

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'WCS Python Client'
copyright = '2025, rasdaman team'
author = wcs.__author__

version = wcs.__version__
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'autoapi.extension',
    'recommonmark',
    'sphinx.ext.intersphinx',
]
autosummary_generate = True  # Turn on sphinx.ext.autosummary
autoclass_content = "both"  # Add __init__ doc (ie. params) to class summaries
html_show_sourcelink = False  # Remove 'view source code' from top of page (for html, not python)
autodoc_inherit_docstrings = False  # If no docstring, inherit from base class
autodoc_typehints = 'description'
add_module_names = False  # Remove namespaces from class/method signatures
intersphinx_mapping = {
    'requests': ('https://docs.python-requests.org/en/latest/', None),
    'python': ('https://docs.python.org/3', None),
}

autoapi_dirs = ['../wcs']
autoapi_options = ['members', 'undoc-members', 'show-inheritance', 'show-module-summary']
autoapi_python_class_content = 'both'
autoapi_keep_files = True  # Helps with debugging

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.venv']

language = 'en'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'
