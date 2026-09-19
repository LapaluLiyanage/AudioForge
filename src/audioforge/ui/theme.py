"""Dark theme for the whole application.

Palette and component shapes come from the AudioForge Claude Design canvas
(icon sidebar, card-grid queue, pill-shaped segmented controls).
"""

BG_APP = "#0F1112"
BG_SHELL = "#1A1D1E"
BG_SIDEBAR_ICON = "#242829"
BG_PANEL = "#17191A"
BG_CARD = "#1C2021"
BG_INPUT = "#242829"
BG_WAVEFORM = "#202425"
BG_WAVEFORM_STRIPE = "#262A2B"

BORDER = "#262A2B"
BORDER_STRONG = "#33383A"
BORDER_HOVER = "#3D4244"

TEXT_PRIMARY = "#EDEAE2"
TEXT_SECONDARY = "#8D9294"
TEXT_FAINT = "#6E7476"

ACCENT = "#E8A33D"
ACCENT_HOVER = "#F2B75C"
ACCENT_TINT = "rgba(232,163,61,0.16)"
TEAL = "#3FA79E"
TEAL_TINT = "rgba(63,167,158,0.16)"
RED = "#D9564A"

FONT_UI = "'Inter Tight','Segoe UI',Helvetica,sans-serif"
FONT_MONO = "'IBM Plex Mono','Consolas',monospace"

DARK_STYLESHEET = f"""
QWidget {{
    background-color: {BG_SHELL};
    color: {TEXT_PRIMARY};
    font-family: {FONT_UI};
    font-size: 13px;
}}
QMainWindow {{ background-color: {BG_APP}; }}

/* Plain labels must not paint the generic QWidget background over whatever
   panel/card they sit on -- specific #objectName rules below still win. */
QLabel {{ background: transparent; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QFrame#sidebar {{ background: {BG_SHELL}; border-right: 1px solid {BORDER}; }}
QFrame#rightPanel {{ background: {BG_PANEL}; border-left: 1px solid {BORDER}; }}
QFrame#card {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 18px; }}
QFrame#outputCard {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 18px; }}

QLabel#logo {{
    background: {ACCENT}; color: {BG_SHELL}; font-weight: 700; font-size: 15px;
    border-radius: 10px;
}}
QPushButton#sidebarIcon {{ background: transparent; border: none; border-radius: 12px; }}
QPushButton#sidebarIcon:hover {{ background: {BG_SIDEBAR_ICON}; }}
QPushButton#sidebarIcon:checked {{ background: {BG_SIDEBAR_ICON}; }}

QLabel#screenTitle {{ font-size: 19px; font-weight: 700; }}
QLabel#statusPill {{
    background: {ACCENT_TINT}; color: {ACCENT}; font-size: 12px; font-weight: 600;
    padding: 6px 14px; border-radius: 100px;
}}
QLabel#cardTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#fieldLabel {{ font-size: 12px; color: {TEXT_SECONDARY}; }}
QLabel#emptyState {{ color: {TEXT_SECONDARY}; }}

QLineEdit {{
    background: {BG_INPUT}; border: 1px solid {BORDER_STRONG}; border-radius: 100px;
    padding: 10px 16px; color: {TEXT_PRIMARY}; font-family: {FONT_MONO}; font-size: 12px;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QPushButton {{
    background-color: {BG_SIDEBAR_ICON}; border: 1px solid {BORDER_STRONG};
    padding: 6px 12px; border-radius: 6px; color: {TEXT_PRIMARY};
}}
QPushButton:hover {{ background-color: {BORDER_HOVER}; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; }}

QPushButton[segment="true"] {{
    font-family: {FONT_UI}; font-size: 12px; font-weight: 500; padding: 8px 14px;
    border: 1px solid {BORDER_STRONG}; border-radius: 999px; background: transparent;
    color: {TEXT_SECONDARY};
}}
QPushButton[segment="true"]:hover {{ border-color: {BORDER_HOVER}; }}
QPushButton[segment="true"]:checked {{
    border-color: {TEAL}; background: {TEAL_TINT}; color: {TEAL};
}}

QPushButton[cta="primary"] {{
    background: {ACCENT}; border: none; border-radius: 999px; color: {BG_SHELL};
    font-family: {FONT_UI}; font-size: 13px; font-weight: 600; padding: 13px;
}}
QPushButton[cta="primary"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[cta="primary"]:disabled {{ background: {BORDER_STRONG}; color: {TEXT_FAINT}; }}

QPushButton[cta="secondary"] {{
    background: transparent; border: 1px solid {BORDER_STRONG}; border-radius: 999px;
    color: {TEXT_PRIMARY}; font-family: {FONT_UI}; font-size: 13px; font-weight: 600; padding: 13px;
}}
QPushButton[cta="secondary"]:hover {{ background: {BG_SIDEBAR_ICON}; border-color: {BORDER_HOVER}; }}
QPushButton[cta="secondary"]:disabled {{ color: {TEXT_FAINT}; border-color: {BORDER}; }}

QFrame#dropzone {{ border: 1px dashed {BORDER_STRONG}; border-radius: 12px; background: transparent; }}
QFrame#dropzone QLabel {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
QFrame#dropzone:hover {{ border-color: {ACCENT}; }}

QFrame#queueCard {{ background: {BG_WAVEFORM}; border: 1px solid {BORDER}; border-radius: 18px; }}
QFrame#queueArt {{
    background: {BG_WAVEFORM_STRIPE}; border-top-left-radius: 18px; border-top-right-radius: 18px;
}}
QLabel#cardMeta {{ font-family: {FONT_MONO}; font-size: 11px; color: {TEXT_SECONDARY}; }}
QLabel#cardError {{ font-size: 11px; color: {RED}; }}

QComboBox, QSpinBox {{
    background-color: {BG_INPUT}; border: 1px solid {BORDER_STRONG}; padding: 4px; border-radius: 6px;
}}
QProgressBar {{ border: 1px solid {BORDER_STRONG}; border-radius: 3px; text-align: center; }}
QProgressBar::chunk {{ background-color: {ACCENT}; }}
"""
