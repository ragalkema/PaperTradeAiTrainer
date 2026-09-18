"""Small reusable widgets shared by pages."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(16, 14, 16, 14)
        self.content.setSpacing(10)
        if title:
            label = QLabel(title.upper())
            label.setObjectName("cardTitle")
            self.content.addWidget(label)


class MetricCard(Card):
    def __init__(self, title: str, value: str = "N/A", note: str = "Waiting for data") -> None:
        super().__init__(title)
        self.value = QLabel(value)
        self.value.setObjectName("metric")
        self.note = QLabel(note)
        self.note.setObjectName("muted")
        self.content.addWidget(self.value)
        self.content.addWidget(self.note)

    def set_metric(self, value: str, note: str) -> None:
        self.value.setText(value)
        self.note.setText(note)


class EmptyState(QWidget):
    def __init__(self, title: str, detail: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #d7e0ea;")
        detail_label = QLabel(detail)
        detail_label.setObjectName("muted")
        detail_label.setWordWrap(True)
        detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(detail_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()


class SectionTitle(QWidget):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        labels = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        labels.addWidget(heading)
        if subtitle:
            detail = QLabel(subtitle)
            detail.setObjectName("muted")
            labels.addWidget(detail)
        row.addLayout(labels)
        row.addStretch()
