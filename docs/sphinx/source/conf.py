"""Sphinx configuration for AURA Platform documentation."""
import os
import sys
import shutil

# ── Path setup ────────────────────────────────────────────────────────────────
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
temp_api_dir = os.path.join(os.path.dirname(__file__), "api_gateway_service")

# Dynamic copy of api-gateway/app to api_gateway_service for clean namespace API docs
if os.path.exists(temp_api_dir):
    try:
        shutil.rmtree(temp_api_dir)
    except Exception:
        pass

src_app = os.path.join(_root, "services/api-gateway/app")
shutil.copytree(src_app, temp_api_dir)

sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "services/api-gateway"))
sys.path.insert(0, os.path.dirname(__file__))

# ── Project info ──────────────────────────────────────────────────────────────
project   = "AURA Platform"
copyright = "2025, AURA Project"
author    = "AURA Team"
release   = "0.1.0"

# ── Extensions ────────────────────────────────────────────────────────────────
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",        # Google / NumPy docstring styles
    "sphinx.ext.viewcode",        # [source] links
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "autoapi.extension",          # sphinx-autoapi: zero-config API docs
    "myst_parser",                # Markdown support for .md files
]

# ── autoapi ───────────────────────────────────────────────────────────────────
autoapi_type              = "python"
autoapi_dirs              = [temp_api_dir]
autoapi_keep_files        = False
autoapi_options           = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]
autoapi_ignore            = ["*/proto_gen/*", "*migrations*", "*__pycache__*"]
autoapi_python_class_content = "both"   # include both class and __init__ docstrings

# ── Napoleon (docstring style) ────────────────────────────────────────────────
napoleon_google_docstring = True
napoleon_numpy_docstring  = False
napoleon_include_init_with_doc = True
napoleon_use_rtype        = True

# ── Intersphinx ───────────────────────────────────────────────────────────────
intersphinx_mapping = {
    "python":    ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

# ── General ───────────────────────────────────────────────────────────────────
templates_path    = ["_templates"]
exclude_patterns  = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix     = {".rst": "restructuredtext", ".md": "markdown"}
master_doc        = "index"

# ── HTML output ───────────────────────────────────────────────────────────────
html_theme         = "furo"
html_static_path   = ["_static"]
html_title         = "AURA Platform"
html_theme_options = {
    "sidebar_hide_name":    False,
    "light_css_variables": {
        "color-brand-primary":   "#6366f1",
        "color-brand-content":   "#6366f1",
    },
    "dark_css_variables": {
        "color-brand-primary":   "#818cf8",
        "color-brand-content":   "#818cf8",
    },
    "source_repository":   "https://github.com/YOUR_USERNAME/aura-platform/",
    "source_branch":       "main",
    "source_directory":    "docs/sphinx/source/",
}
todo_include_todos = True

# Suppress known autoapi duplicate-field warnings for dataclasses
suppress_warnings = [
    "autoapi",
    "ref.duplicate",
]
