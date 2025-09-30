
# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
import os
import sys

# -- Project information -----------------------------------------------------

project = 'SMS España Connector'
copyright = '2025, Rafael Solitario' 
author = 'Rafael Solitario'

# La versión corta X.Y
version = '1.0'
# La versión completa, 
release = '1.0.0'


# -- General configuration ---------------------------------------------------

# extensiones sphinx
extensions = []

# Rutas que contienen plantillas, relativas a este directorio.
templates_path = ['_templates']
# El sufijo de los archivos fuente.
source_suffix = '.rst'
# El documento maestro, es decir, el que contiene la raíz de la tabla de contenidos.
master_doc = 'index'

# El idioma de la documentación
language = 'es'

# Lista de patrones, relativos al directorio fuente, que se ignoran al buscar archivos.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# El tema a utilizar para las páginas de ayuda HTML.
# Hemos instalado sphinx_rtd_theme, así que lo usamos.
html_theme = 'sphinx_rtd_theme'

# Rutas que contienen archivos estáticos personalizados (como hojas de estilo o imágenes).
html_static_path = ['_static']

# ---
# instalación de sphinx
# pip install sphinx sphinx-rtd-theme
# creando documentación: sphinx-build -b html . _build