"""Accessible dark theme with restrained trading accents."""

DARK_STYLESHEET = """
* { font-family: "Segoe UI", sans-serif; font-size: 13px; color: #d7e0ea; }
QMainWindow, QWidget { background: #0b111a; }
QFrame#sidebar { background: #0e1622; border-right: 1px solid #223044; }
QFrame#topbar { background: #0e1622; border-bottom: 1px solid #223044; }
QLabel#brand { font-size: 18px; font-weight: 700; color: #f5f8fb; }
QLabel#pageTitle { font-size: 24px; font-weight: 650; color: #f5f8fb; }
QLabel#muted { color: #8392a5; }
QLabel#paperBadge { background: #123f3a; color: #70e1c1; border: 1px solid #247869;
  border-radius: 12px; padding: 5px 11px; font-weight: 700; }
QLabel#statusError { background: #3b2026; color: #ff9aaa; padding: 8px; border-radius: 5px; }
QPushButton#nav { text-align: left; padding: 10px 14px; border: 0; border-radius: 6px;
  color: #91a0b4; background: transparent; }
QPushButton#nav:hover { background: #172233; color: #ffffff; }
QPushButton#nav:checked { background: #183247; color: #65d8ff; border-left: 3px solid #2cc6f4; }
QPushButton { background: #182638; border: 1px solid #2a3b51; border-radius: 5px;
  padding: 7px 12px; }
QPushButton:hover { background: #21344b; }
QPushButton:disabled { color: #566375; background: #121b28; }
QFrame#card { background: #101925; border: 1px solid #223044; border-radius: 8px; }
QLabel#cardTitle { color: #8291a4; font-size: 11px; font-weight: 700; }
QLabel#metric { color: #f5f8fb; font-size: 22px; font-weight: 650; }
QTableWidget { background: #101925; alternate-background-color: #121e2c; gridline-color: #223044;
  border: 1px solid #223044; border-radius: 7px; selection-background-color: #1b4b64; }
QHeaderView::section { background: #131f2e; color: #91a0b4; padding: 8px; border: 0;
  border-bottom: 1px solid #2a3b51; font-weight: 600; }
QTabWidget::pane { border: 1px solid #223044; }
QTabBar::tab { padding: 8px 14px; background: #101925; color: #8392a5; }
QTabBar::tab:selected { color: #65d8ff; border-bottom: 2px solid #2cc6f4; }
QComboBox, QLineEdit, QDoubleSpinBox { background: #101925; border: 1px solid #2a3b51;
  border-radius: 5px; padding: 6px; }
QScrollArea { border: 0; }
QToolTip { background: #1a2737; color: white; border: 1px solid #3b5069; }
"""
