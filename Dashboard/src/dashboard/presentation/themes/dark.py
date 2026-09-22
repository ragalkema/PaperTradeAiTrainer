"""Dense exchange-inspired dark theme for the desktop research terminal."""

DARK_STYLESHEET = """
* { font-family: "Segoe UI", sans-serif; font-size: 13px; color: #dfe5ee; }
QMainWindow, QWidget { background: #0b0e14; }
QFrame#sidebar { background: #10141d; border-right: 1px solid #242a36; }
QFrame#topbar { background: #10141d; border-bottom: 1px solid #242a36; }
QLabel#brand { font-size: 18px; font-weight: 750; letter-spacing: 1px; color: #ffffff; }
QLabel#brandDetail { font-size: 10px; font-weight: 700; letter-spacing: 2px; color: #728096; }
QLabel#navSection { color: #586477; font-size: 10px; font-weight: 700; letter-spacing: 1px;
  padding: 15px 10px 6px 10px; }
QLabel#breadcrumb { font-size: 15px; font-weight: 650; color: #f7f9fc; }
QLabel#workspace { color: #657185; font-size: 11px; font-weight: 600; }
QLabel#connectionState { background: #122b25; color: #47d7ac; border: 1px solid #205444;
  border-radius: 11px; padding: 4px 10px; font-size: 10px; font-weight: 700; }
QLabel#pageTitle { font-size: 25px; font-weight: 650; color: #f7f9fc; }
QLabel#muted { color: #7d899c; }
QLabel#paperBadge { background: #18243f; color: #8caeff; border: 1px solid #2a477c;
  border-radius: 11px; padding: 5px 10px; font-size: 10px; font-weight: 700; }
QLabel#statusError { background: #32191f; color: #ff8698; padding: 9px 26px; }
QPushButton#nav { text-align: left; min-height: 20px; padding: 8px 12px; border: 0;
  border-radius: 6px; color: #919caf; background: transparent; }
QPushButton#nav:hover { background: #191f2a; color: #f7f9fc; }
QPushButton#nav:checked { background: #202a3a; color: #ffffff; border-left: 3px solid #4f7cff;
  font-weight: 600; }
QPushButton { background: #1a2230; border: 1px solid #303b4d; border-radius: 6px;
  padding: 8px 13px; font-weight: 600; }
QPushButton:hover { background: #232e40; border-color: #44536b; }
QPushButton:disabled { color: #525b69; background: #121722; border-color: #222936; }
QFrame#card { background: #121720; border: 1px solid #252c38; border-radius: 8px; }
QFrame#card:hover { border-color: #343e4e; }
QLabel#cardTitle { color: #7e899a; font-size: 10px; font-weight: 700; letter-spacing: .7px; }
QLabel#metric { color: #f7f9fc; font-size: 23px; font-weight: 650; }
QTableWidget { background: #11161f; alternate-background-color: #141a24;
  gridline-color: transparent;
  border: 1px solid #252c38; border-radius: 7px; selection-background-color: #243554;
  selection-color: #ffffff; outline: 0; }
QTableWidget::item { padding: 7px; border-bottom: 1px solid #1f2631; }
QHeaderView::section { background: #171d27; color: #7f8b9e; padding: 9px 8px; border: 0;
  border-bottom: 1px solid #2b3442; font-size: 10px; font-weight: 700; }
QTabWidget::pane { border: 1px solid #252c38; }
QTabBar::tab { padding: 9px 15px; background: #11161f; color: #7d899c; }
QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid #4f7cff; }
QComboBox, QLineEdit, QDoubleSpinBox { min-height: 20px; background: #151b25;
  border: 1px solid #303949; border-radius: 6px; padding: 6px 10px; }
QComboBox:hover, QLineEdit:hover, QDoubleSpinBox:hover { border-color: #4a5870; }
QComboBox::drop-down { border: 0; width: 24px; }
QGroupBox { border: 1px solid #252c38; border-radius: 8px; margin-top: 12px; padding: 14px; }
QGroupBox::title { color: #a7b1c0; subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QScrollBar:vertical { background: #0f141c; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #303949; border-radius: 5px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollArea { border: 0; }
QToolTip { background: #1a2230; color: white; border: 1px solid #3b465a; padding: 5px; }
"""
