"""Sphinx configuration for AURA Platform documentation."""
import os
import sys
import shutil

# ── Path setup ────────────────────────────────────────────────────────────────
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

dynamic_packages = {
    "api_gateway_service": os.path.join(_root, "services/api-gateway/app"),
    "registry_service": os.path.join(_root, "services/registry-service/app"),
    "mlops_service": os.path.join(_root, "services/mlops-service/app"),
    "edge_connector_service": os.path.join(_root, "services/edge-connector-service/app"),
    "edge_runtime": os.path.join(_root, "edge-runtime"),
    "shared": os.path.join(_root, "shared"),
}

autoapi_dirs = []

for name, src in dynamic_packages.items():
    dest = os.path.join(os.path.dirname(__file__), name)
    if os.path.exists(dest):
        try:
            shutil.rmtree(dest)
        except Exception:
            pass
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "build", "dist", ".doctrees", "html"))
    
    # Ensure __init__.py exists recursively in all subdirectories under dest
    for root_dir, dirs, files in os.walk(dest):
        init_file = os.path.join(root_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                f.write("# Auto-generated package init\n")
            
    autoapi_dirs.append(dest)

sys.path.insert(0, _root)
for svc in [
    "services/api-gateway",
    "services/registry-service",
    "services/mlops-service",
    "services/edge-connector-service",
    "edge-runtime",
]:
    sys.path.insert(0, os.path.join(_root, svc))
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
autoapi_dirs              = autoapi_dirs
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
