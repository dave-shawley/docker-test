#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import alabaster
import dockertest


project = 'dockertest'
copyright = '2015, Dave Shawley'
version = dockertest.__version__
release = '.'.join(str(x) for x in dockertest.version_info[:2])

needs_sphinx = '1.0'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]
templates_path = []
source_suffix = '.rst'
source_encoding = 'utf-8-sig'
master_doc = 'index'
pygments_style = 'sphinx'
html_theme = 'alabaster'
html_theme_path = [alabaster.get_path()]
html_static_path = []
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'searchbox.html',
    ],
}
html_theme_options = {
    'description': 'Make docker-compose machines available in tests',
    'github_banner': True,
    'github_button': True,
    'travis_button': True,
    'github_user': 'dave-shawley',
    'github_repo': 'docker-test',
}

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
}
