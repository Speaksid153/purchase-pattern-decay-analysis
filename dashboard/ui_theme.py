from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

THEME_CSS = """
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script id="tailwind-config">
    tailwind.config = {
        darkMode: "class",
        theme: {
            extend: {
                colors: {
                    "on-secondary-container": "#2d7146",
                    "outline-variant": "#c4c7c7",
                    "tertiary-fixed": "#e6e1df",
                    "on-secondary": "#ffffff",
                    "primary-container": "#1c1b1b",
                    "tertiary": "#000000",
                    "on-primary-fixed-variant": "#474646",
                    "on-tertiary-fixed-variant": "#484645",
                    "outline": "#747878",
                    "inverse-primary": "#c8c6c5",
                    "secondary-fixed": "#abf3bd",
                    "secondary": "#266b41",
                    "surface-tint": "#5f5e5e",
                    "surface-container-low": "#f4f3f1",
                    "primary": "#000000",
                    "surface-container-high": "#e9e8e6",
                    "on-tertiary-fixed": "#1c1b1a",
                    "primary-fixed-dim": "#c8c6c5",
                    "on-surface-variant": "#444748",
                    "on-primary-container": "#858383",
                    "on-secondary-fixed": "#00210e",
                    "surface-bright": "#faf9f7",
                    "error-container": "#ffdad6",
                    "inverse-surface": "#2f3130",
                    "surface-container-highest": "#e3e2e0",
                    "secondary-fixed-dim": "#90d6a3",
                    "error": "#ba1a1a",
                    "on-error": "#ffffff",
                    "surface-dim": "#dadad8",
                    "surface": "#faf9f7",
                    "secondary-container": "#abf3bd",
                    "surface-container": "#efeeec",
                    "tertiary-container": "#1c1b1a",
                    "on-primary-fixed": "#1c1b1b",
                    "tertiary-fixed-dim": "#cac6c4",
                    "on-primary": "#ffffff",
                    "inverse-on-surface": "#f1f1ef",
                    "surface-container-lowest": "#ffffff",
                    "on-secondary-fixed-variant": "#02522b",
                    "on-tertiary-container": "#868381",
                    "on-error-container": "#93000a",
                    "background": "#faf9f7",
                    "primary-fixed": "#e5e2e1",
                    "surface-variant": "#e3e2e0",
                    "on-tertiary": "#ffffff",
                    "on-background": "#1a1c1b",
                    "on-surface": "#1a1c1b"
                },
                borderRadius: {
                    "DEFAULT": "0.125rem",
                    "lg": "0.25rem",
                    "xl": "0.5rem",
                    "full": "0.75rem"
                },
                fontFamily: {
                    "headline-lg": ["Inter", "sans-serif"],
                    "label-sm": ["IBM Plex Sans", "sans-serif"],
                    "display-tabular": ["IBM Plex Sans", "sans-serif"],
                    "table-data": ["IBM Plex Sans", "sans-serif"],
                    "body-md": ["Inter", "sans-serif"],
                    "headline-md": ["Inter", "sans-serif"]
                }
            }
        }
    }
</script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=IBM+Plex+Sans:wght@450;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>

<style>
    .material-symbols-outlined {
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        display: inline-block;
        vertical-align: middle;
    }

    /* Streamlit core layout overrides */
    .stApp {
        background-color: #faf9f7 !important;
        color: #1a1c1b !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    header[data-testid="stHeader"] {
        display: none !important;
    }

    .main .block-container {
        padding-top: 5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1280px !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f4f3f1 !important;
        border-right: 1px solid #c4c7c7 !important;
        padding-top: 2rem !important;
    }

    section[data-testid="stSidebar"] .stMarkdown h1, 
    section[data-testid="stSidebar"] .stMarkdown h2, 
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: #1a1c1b !important;
    }

    /* Override dataframe & table styling */
    .stDataFrame {
        border: 1px solid #c4c7c7 !important;
        border-radius: 0.25rem !important;
        background-color: #ffffff !important;
    }
    
    /* Override info box styling */
    div[data-testid="stNotification"] {
        background-color: #ffffff !important;
        border: 1px solid #c4c7c7 !important;
        border-radius: 0.5rem !important;
        color: #1a1c1b !important;
        box-shadow: none !important;
    }
    
    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        background-color: #ffffff !important;
        color: #1a1c1b !important;
        border: 1px solid #c4c7c7 !important;
        border-radius: 0.25rem !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: #1a1c1b !important;
        background-color: #f4f3f1 !important;
    }
</style>
"""


def apply_theme():
    """Inject Tailwind, custom fonts, and global design system styles."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    apply_matplotlib_theme()


def apply_matplotlib_theme():
    """Style matplotlib figures to harmonize perfectly with the Design System."""
    plt.rcParams.update({
        "figure.facecolor": "#faf9f7",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#c4c7c7",
        "axes.labelcolor": "#1a1c1b",
        "axes.titlecolor": "#1a1c1b",
        "xtick.color": "#444748",
        "ytick.color": "#444748",
        "grid.color": "#e3e2e0",
        "grid.alpha": 0.6,
        "font.family": "sans-serif",
        "font.sans-serif": ["IBM Plex Sans", "Inter", "DejaVu Sans", "Arial"],
        "text.color": "#1a1c1b",
    })


def render_top_navbar(active_page: str = "Portfolio Risk"):
    """Render top navigation bar component matching the HTML Design System."""
    link_portfolio = "border-b-2 border-primary text-primary font-bold" if active_page == "Portfolio Risk" else "text-on-surface-variant hover:text-primary"
    link_detail = "border-b-2 border-primary text-primary font-bold" if active_page == "Customer Detail" else "text-on-surface-variant hover:text-primary"
    link_comparison = "border-b-2 border-primary text-primary font-bold" if active_page == "Model Comparison" else "text-on-surface-variant hover:text-primary"

    navbar_html = f"""
    <header class="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-[40px] h-[56px] bg-[#faf9f7] border-b border-[#c4c7c7]">
        <div class="flex items-center gap-8 h-full">
            <span class="font-bold text-[18px] text-[#000000] font-headline-md tracking-tight">Early Churn Predictor</span>
            <nav class="flex items-center gap-6 h-full">
                <span class="h-full flex items-center px-2 text-[12px] font-medium font-label-sm uppercase tracking-wider {link_portfolio}">Portfolio Risk</span>
                <span class="h-full flex items-center px-2 text-[12px] font-medium font-label-sm uppercase tracking-wider {link_detail}">Customer Detail</span>
                <span class="h-full flex items-center px-2 text-[12px] font-medium font-label-sm uppercase tracking-wider {link_comparison}">Model Comparison</span>
            </nav>
        </div>
        <div class="flex items-center">
            <span class="text-[12px] font-medium text-[#444748] bg-[#efeeec] px-3 py-1 rounded border border-[#c4c7c7]">Deterministic Analytics Engine</span>
        </div>
    </header>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)
