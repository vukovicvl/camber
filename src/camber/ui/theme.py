"""Camber dark monitoring theme — industrial/utilitarian aesthetic."""

COLORS = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_card": "#1C2333",
    "bg_input": "#0D1117",
    "border": "#30363D",
    "border_light": "#3D444D",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    "accent": "#00BAFF",
    "accent_hover": "#33C8FF",
    "ok": "#2ECC71",
    "warning": "#F1C40F",
    "critical": "#E74C3C",
    "unknown": "#6E7681",
}

STATUS_COLORS = {
    "ok": COLORS["ok"],
    "warning": COLORS["warning"],
    "critical": COLORS["critical"],
    "unknown": COLORS["unknown"],
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'Consolas', monospace;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    background: {COLORS['bg_primary']};
    border-radius: 4px;
}}

QTabBar::tab {{
    background: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: bold;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QTabBar::tab:selected {{
    background: {COLORS['bg_card']};
    color: {COLORS['accent']};
    border-bottom: 2px solid {COLORS['accent']};
}}

QTabBar::tab:hover:!selected {{
    background: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
}}

QPushButton {{
    background: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    padding: 8px 20px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 12px;
}}

QPushButton:hover {{
    background: {COLORS['accent']};
    color: {COLORS['bg_primary']};
    border-color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background: {COLORS['accent_hover']};
}}

QPushButton#btnPrimary {{
    background: {COLORS['accent']};
    color: {COLORS['bg_primary']};
    border: none;
}}

QLabel {{
    color: {COLORS['text_primary']};
}}

QLabel#labelMuted {{
    color: {COLORS['text_secondary']};
    font-size: 11px;
}}

QLabel#labelHeader {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['text_primary']};
    padding: 4px 0;
}}

QLabel#labelSubheader {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
    padding: 2px 0;
}}

QListWidget, QTableWidget, QTreeWidget {{
    background: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 4px;
    outline: none;
}}

QListWidget::item, QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {COLORS['border']};
}}

QListWidget::item:selected, QTableWidget::item:selected {{
    background: {COLORS['bg_card']};
    color: {COLORS['accent']};
}}

QListWidget::item:hover, QTableWidget::item:hover {{
    background: {COLORS['bg_card']};
}}

QHeaderView::section {{
    background: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    padding: 8px 12px;
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QComboBox {{
    background: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 160px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['bg_card']};
    selection-color: {COLORS['accent']};
}}

QScrollBar:vertical {{
    background: {COLORS['bg_primary']};
    width: 8px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QFileDialog {{
    background: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
}}

QMessageBox {{
    background: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
}}

QToolTip {{
    background: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    padding: 6px;
    font-size: 12px;
}}

QStatusBar {{
    background: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
    font-size: 11px;
}}

QSplitter::handle {{
    background: {COLORS['border']};
    width: 2px;
}}
"""
