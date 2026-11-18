# coding: utf-8
"""Palette et polices de l'IHM (affichage uniquement)."""

import tkinter as tk
from tkinter import ttk

# --- Couleurs (thème sombre) ---
BG            = "#0f172a"   # fond fenêtre
SURFACE       = "#1e293b"   # cartes / panneaux
SURFACE_2     = "#273449"   # boutons secondaires
BORDER        = "#334155"
TEXT          = "#e2e8f0"
MUTED         = "#94a3b8"
ACCENT        = "#3b82f6"
ACCENT_ACTIVE = "#2563eb"
DANGER        = "#ef4444"
DANGER_ACTIVE = "#dc2626"
SUCCESS       = "#10b981"
SUCCESS_ACTIVE = "#059669"

PLOT_BG       = "#0b1220"
GRID          = "#1c2740"
AXIS          = "#475569"

SPEED         = "#38bdf8"   # courbe / valeur vitesse
CURRENT       = "#34d399"   # courbe / valeur courant
REFERENCE     = "#f87171"   # consigne
MARKER        = "#fbbf24"   # repères temps début / fin

# Couleurs passées par les contrôleurs -> couleurs du thème
CURVE_COLORS = {
    "blue":  SPEED,
    "green": CURRENT,
    "red":   REFERENCE,
}

# --- Polices ---
FONT_FAMILY = "Segoe UI"
FONT        = (FONT_FAMILY, 10)
FONT_SMALL  = (FONT_FAMILY, 8)
FONT_BOLD   = (FONT_FAMILY, 10, "bold")
FONT_KPI    = (FONT_FAMILY, 20, "bold")
FONT_CAPTION = (FONT_FAMILY, 8, "bold")
FONT_TITLE  = (FONT_FAMILY, 26, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 12)


def apply_ttk(root):
    """Style des widgets ttk (Combobox) et de leur liste déroulante."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE_2,
        foreground=TEXT,
        arrowcolor=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", SURFACE), ("!disabled", SURFACE)],
        foreground=[("!disabled", TEXT)],
        selectbackground=[("!disabled", SURFACE)],
        selectforeground=[("!disabled", TEXT)],
        background=[("active", ACCENT)],
    )
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    root.option_add("*TCombobox*Listbox.font", FONT)
