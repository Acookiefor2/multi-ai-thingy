"""
Council - Main UI
Dark terminal aesthetic, color-coded by model.
"""

import sys
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QFrame, QDialog,
    QFormLayout, QTabWidget, QScrollArea, QSizePolicy, QComboBox,
    QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCursor, QPalette, QIcon, QTextCharFormat

from core.context_manager import ContextManager, MODEL_COLORS, MODEL_LABELS
from core.router import parse_target, resolve_targets
from core.adapters.claude import ClaudeAdapter
from core.adapters.openai_adapter import GPTAdapter
from core.adapters.gemini import GeminiAdapter

# ── Palette ────────────────────────────────────────────────────────────────────
BG_DARK    = "#0D0D0F"
BG_MID     = "#13131A"
BG_PANEL   = "#1A1A24"
BG_INPUT   = "#111118"
BORDER     = "#2A2A3A"
TEXT_MAIN  = "#E8E8F0"
TEXT_DIM   = "#555568"
ACCENT     = "#FF8C42"   # Claude orange as primary accent

MODEL_BG = {
    "claude": "#1A1208",
    "gpt":    "#081A10",
    "gemini": "#08101A",
    "user":   "#0D0D0F",
    "system": "#111118",
}


# ── Worker Thread ──────────────────────────────────────────────────────────────
class ModelWorker(QThread):
    response_ready = pyqtSignal(str, str)   # (model_name, response_text)
    error_occurred = pyqtSignal(str, str)   # (model_name, error_text)
    finished_all   = pyqtSignal()

    def __init__(self, targets: list, adapters: dict, context: ContextManager, message: str):
        super().__init__()
        self.targets  = targets
        self.adapters = adapters
        self.context  = context
        self.message  = message

    def run(self):
        threads = []
        for model in self.targets:
            t = threading.Thread(target=self._call_model, args=(model,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.finished_all.emit()

    def _call_model(self, model: str):
        try:
            adapter  = self.adapters[model]
            history  = self.context.get_for_model(model)
            system   = self.context.get_system_prompt(model)
            response = adapter.send(history, system, self.message)
            self.response_ready.emit(model, response)
        except Exception as e:
            self.error_occurred.emit(model, str(e))


# ── Settings Dialog ────────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, keys: dict, parent=None):
        super().__init__(parent)
        self.keys = dict(keys)
        self.setWindowTitle("Council — API Keys")
        self.setMinimumWidth(480)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG_PANEL}; color: {TEXT_MAIN}; }}
            QLabel  {{ color: {TEXT_MAIN}; font-size: 13px; }}
            QLineEdit {{
                background: {BG_INPUT}; color: {TEXT_MAIN};
                border: 1px solid {BORDER}; border-radius: 6px;
                padding: 8px 12px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
            QPushButton {{
                background: {ACCENT}; color: #000; font-weight: bold;
                border: none; border-radius: 6px; padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #ffA060; }}
            QPushButton#cancel {{
                background: {BG_INPUT}; color: {TEXT_MAIN};
                border: 1px solid {BORDER};
            }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("API Keys")
        title.setFont(QFont("Courier New", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(title)

        sub = QLabel("Keys are stored in memory only — not saved to disk.")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)

        self.fields = {}
        model_info = [
            ("claude", "Claude (Anthropic)",    MODEL_COLORS["claude"]),
            ("gpt",    "GPT (OpenAI)",          MODEL_COLORS["gpt"]),
            ("gemini", "Gemini (Google)",        MODEL_COLORS["gemini"]),
        ]

        for key, label, color in model_info:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            field = QLineEdit(self.keys.get(key, ""))
            field.setPlaceholderText(f"Enter {label} API key...")
            field.setEchoMode(QLineEdit.Password)
            self.fields[key] = field
            form.addRow(lbl, field)

        layout.addLayout(form)

        # Model selectors
        model_row = QHBoxLayout()
        model_row.setSpacing(12)

        self.model_selects = {}
        model_defaults = {
            "claude": ("claude-sonnet-4-5", ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5-20251001"]),
            "gpt":    ("gpt-4o",            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]),
            "gemini": ("gemini-1.5-pro",    ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]),
        }

        for key, (default, options) in model_defaults.items():
            col = QVBoxLayout()
            lbl = QLabel(key.upper())
            lbl.setStyleSheet(f"color: {MODEL_COLORS[key]}; font-size: 11px; font-weight: bold;")
            combo = QComboBox()
            combo.addItems(options)
            combo.setCurrentText(default)
            combo.setStyleSheet(f"""
                QComboBox {{
                    background: {BG_INPUT}; color: {TEXT_MAIN};
                    border: 1px solid {BORDER}; border-radius: 4px;
                    padding: 4px 8px; font-size: 11px;
                }}
                QComboBox::drop-down {{ border: none; }}
                QComboBox QAbstractItemView {{
                    background: {BG_PANEL}; color: {TEXT_MAIN};
                    selection-background-color: {BORDER};
                }}
            """)
            self.model_selects[key] = combo
            col.addWidget(lbl)
            col.addWidget(combo)
            model_row.addLayout(col)

        layout.addLayout(model_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Keys")
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def get_keys(self):
        return {k: v.text().strip() for k, v in self.fields.items()}

    def get_models(self):
        return {k: v.currentText() for k, v in self.model_selects.items()}


# ── Main Window ────────────────────────────────────────────────────────────────
class CouncilWindow(QMainWindow):
    append_message_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.context   = ContextManager()
        self.api_keys  = {"claude": "", "gpt": "", "gemini": ""}
        self.models    = {"claude": "claude-sonnet-4-5", "gpt": "gpt-4o", "gemini": "gemini-1.5-pro"}
        self.adapters  = {}
        self.last_target = None
        self.worker    = None
        self._thinking_dots = 0
        self._thinking_timer = QTimer()
        self._thinking_timer.timeout.connect(self._pulse_thinking)

        self.setWindowTitle("Council")
        self.setMinimumSize(900, 680)
        self.resize(1100, 760)
        self._apply_global_style()
        self._build_ui()
        self.append_message_signal.connect(self._append_bubble)
        self._show_welcome()

    # ── Styling ──────────────────────────────────────────────────────────────
    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {BG_DARK}; color: {TEXT_MAIN}; }}
            QScrollBar:vertical {{
                background: {BG_MID}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {BORDER}; border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QToolTip {{ background: {BG_PANEL}; color: {TEXT_MAIN}; border: 1px solid {BORDER}; padding: 4px; }}
        """)

    # ── UI Build ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_chat_area(), 1)
        root.addLayout(body)

        root.addWidget(self._build_input_bar())

    def _build_header(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background: {BG_MID}; border-bottom: 1px solid {BORDER};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("⬡ COUNCIL")
        logo.setFont(QFont("Courier New", 15, QFont.Bold))
        logo.setStyleSheet(f"color: {ACCENT}; letter-spacing: 4px;")
        layout.addWidget(logo)

        layout.addStretch()

        self.status_label = QLabel("No keys configured")
        self.status_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self.status_label)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet(f"background: {BORDER};")
        layout.addWidget(sep)

        settings_btn = QPushButton("⚙ Keys")
        settings_btn.setFixedHeight(30)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG_PANEL}; color: {TEXT_MAIN};
                border: 1px solid {BORDER}; border-radius: 5px;
                padding: 0 14px; font-size: 12px;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        """)
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        clear_btn = QPushButton("✕ Clear")
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG_PANEL}; color: {TEXT_DIM};
                border: 1px solid {BORDER}; border-radius: 5px;
                padding: 0 14px; font-size: 12px;
            }}
            QPushButton:hover {{ color: #FF5555; border-color: #FF5555; }}
        """)
        clear_btn.clicked.connect(self._clear_chat)
        layout.addWidget(clear_btn)

        return bar

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"background: {BG_MID}; border-right: 1px solid {BORDER};")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        models_lbl = QLabel("MODELS")
        models_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(models_lbl)

        self.model_indicators = {}
        for model in ["claude", "gpt", "gemini"]:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
            lbl = QLabel(MODEL_LABELS[model])
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
            self.model_indicators[model] = (dot, lbl)
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            layout.addLayout(row)

        layout.addSpacing(16)

        cmds_lbl = QLabel("COMMANDS")
        cmds_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(cmds_lbl)

        commands = [
            ("@claude", MODEL_COLORS["claude"]),
            ("@gpt",    MODEL_COLORS["gpt"]),
            ("@gemini", MODEL_COLORS["gemini"]),
            ("@all",    ACCENT),
        ]
        for cmd, color in commands:
            btn = QPushButton(cmd)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {color};
                    border: 1px solid transparent; border-radius: 4px;
                    padding: 4px 8px; text-align: left; font-size: 12px;
                    font-family: 'Courier New';
                }}
                QPushButton:hover {{ border-color: {color}; background: rgba(255,255,255,0.03); }}
            """)
            btn.clicked.connect(lambda _, c=cmd: self._insert_tag(c))
            layout.addWidget(btn)

        layout.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        return sidebar

    def _build_chat_area(self):
        container = QFrame()
        container.setStyleSheet(f"background: {BG_DARK};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background: {BG_DARK}; color: {TEXT_MAIN};
                border: none; padding: 16px;
                font-family: 'Courier New'; font-size: 13px;
                line-height: 1.6;
            }}
        """)
        layout.addWidget(self.chat_display)

        self.thinking_label = QLabel("")
        self.thinking_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; padding: 4px 20px;")
        layout.addWidget(self.thinking_label)

        return container

    def _build_input_bar(self):
        bar = QFrame()
        bar.setStyleSheet(f"background: {BG_MID}; border-top: 1px solid {BORDER};")
        bar.setFixedHeight(72)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("@claude @gpt @gemini @all  —  type your message...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_INPUT}; color: {TEXT_MAIN};
                border: 1px solid {BORDER}; border-radius: 8px;
                padding: 10px 16px; font-size: 13px;
                font-family: 'Courier New';
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)
        self.input_field.returnPressed.connect(self._send)
        layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send ↵")
        self.send_btn.setFixedSize(90, 44)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #0D0D0F;
                border: none; border-radius: 8px;
                font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{ background: #FFA060; }}
            QPushButton:disabled {{ background: {BORDER}; color: {TEXT_DIM}; }}
        """)
        self.send_btn.clicked.connect(self._send)
        layout.addWidget(self.send_btn)

        return bar

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _rebuild_adapters(self):
        self.adapters = {}
        if self.api_keys.get("claude"):
            self.adapters["claude"] = ClaudeAdapter(self.api_keys["claude"], self.models["claude"])
        if self.api_keys.get("gpt"):
            self.adapters["gpt"] = GPTAdapter(self.api_keys["gpt"], self.models["gpt"])
        if self.api_keys.get("gemini"):
            self.adapters["gemini"] = GeminiAdapter(self.api_keys["gemini"], self.models["gemini"])

        # Update sidebar indicators
        for model, (dot, lbl) in self.model_indicators.items():
            if model in self.adapters:
                color = MODEL_COLORS[model]
                dot.setStyleSheet(f"color: {color}; font-size: 10px;")
                lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            else:
                dot.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
                lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")

        configured = list(self.adapters.keys())
        if configured:
            self.status_label.setText("● " + "  ".join(MODEL_LABELS[m] for m in configured))
            self.status_label.setStyleSheet(f"color: #4CAF82; font-size: 11px;")
        else:
            self.status_label.setText("No keys configured")
            self.status_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")

    def _send(self):
        text = self.input_field.text().strip()
        if not text:
            return
        if not self.adapters:
            self._append_bubble("system", "⚠ No API keys configured. Click '⚙ Keys' to add them.")
            return

        target_raw, cleaned_msg = parse_target(text)
        targets = resolve_targets(target_raw, self.adapters, self.last_target)

        if not targets:
            unknown = target_raw or "unknown"
            self._append_bubble("system", f"⚠ Model '@{unknown}' is not configured or unknown.")
            return

        self.input_field.clear()
        self.context.add("user", text, model_target=targets[0] if len(targets) == 1 else "all")
        self._append_bubble("user", text)

        if len(targets) == 1:
            self.last_target = targets[0]

        self._set_busy(True, targets)

        self.worker = ModelWorker(targets, self.adapters, self.context, cleaned_msg or text)
        self.worker.response_ready.connect(self._on_response)
        self.worker.finished_all.connect(self._on_all_done)
        self.worker.start()

        self._update_stats()

    def _on_response(self, model: str, response: str):
        self.context.add(model, response)
        self.append_message_signal.emit(model, response)

    def _on_all_done(self):
        self._set_busy(False)
        self._update_stats()

    def _set_busy(self, busy: bool, targets: list = None):
        self.send_btn.setEnabled(not busy)
        self.input_field.setEnabled(not busy)
        if busy and targets:
            names = " + ".join(MODEL_LABELS.get(t, t) for t in targets)
            self.thinking_label.setText(f"  {names} is thinking...")
            self._thinking_dots = 0
            self._thinking_timer.start(400)
        else:
            self._thinking_timer.stop()
            self.thinking_label.setText("")

    def _pulse_thinking(self):
        self._thinking_dots = (self._thinking_dots + 1) % 4
        current = self.thinking_label.text().rstrip(".")
        self.thinking_label.setText(current + "." * self._thinking_dots)

    def _append_bubble(self, role: str, content: str):
        color   = MODEL_COLORS.get(role, TEXT_MAIN)
        label   = MODEL_LABELS.get(role, role.upper())
        bg      = MODEL_BG.get(role, BG_DARK)

        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Spacer
        fmt_spacer = QTextCharFormat()
        fmt_spacer.setBackground(QColor(BG_DARK))
        cursor.setCharFormat(fmt_spacer)
        cursor.insertText("\n")

        # Header line
        fmt_header = QTextCharFormat()
        fmt_header.setForeground(QColor(color))
        fmt_header.setBackground(QColor(bg))
        fmt_header.setFontWeight(QFont.Bold)
        fmt_header.setFontPointSize(10)
        cursor.setCharFormat(fmt_header)
        cursor.insertText(f" {label} ")

        fmt_dim = QTextCharFormat()
        fmt_dim.setForeground(QColor(TEXT_DIM))
        fmt_dim.setBackground(QColor(bg))
        fmt_dim.setFontPointSize(9)
        cursor.setCharFormat(fmt_dim)

        from datetime import datetime
        cursor.insertText(f" {datetime.now().strftime('%H:%M')}\n")

        # Body
        fmt_body = QTextCharFormat()
        fmt_body.setForeground(QColor(TEXT_MAIN))
        fmt_body.setBackground(QColor(bg))
        fmt_body.setFontPointSize(12)
        cursor.setCharFormat(fmt_body)
        cursor.insertText(f" {content}\n")

        # Bottom border
        fmt_border = QTextCharFormat()
        fmt_border.setForeground(QColor(BORDER))
        fmt_border.setBackground(QColor(BG_DARK))
        fmt_border.setFontPointSize(8)
        cursor.setCharFormat(fmt_border)
        cursor.insertText("─" * 80 + "\n")

        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def _show_welcome(self):
        welcome = (
            "Welcome to Council — your multi-AI workspace.\n\n"
            "  @claude  →  Talk to Claude (Anthropic)\n"
            "  @gpt     →  Talk to GPT (OpenAI)\n"
            "  @gemini  →  Talk to Gemini (Google)\n"
            "  @all     →  Broadcast to all configured models\n\n"
            "All models share the same conversation history.\n"
            "Click '⚙ Keys' to add your API keys and get started."
        )
        self._append_bubble("system", welcome)

    def _insert_tag(self, tag: str):
        current = self.input_field.text()
        if not current.startswith("@"):
            self.input_field.setText(f"{tag} {current}")
        else:
            parts = current.split(" ", 1)
            rest = parts[1] if len(parts) > 1 else ""
            self.input_field.setText(f"{tag} {rest}")
        self.input_field.setFocus()
        self.input_field.setCursorPosition(len(self.input_field.text()))

    def _update_stats(self):
        stats = self.context.summary_stats()
        lines = []
        for role, count in stats.items():
            if role != "system":
                lbl = MODEL_LABELS.get(role, role)
                lines.append(f"{lbl}: {count}")
        self.stats_label.setText("\n".join(lines))

    def _open_settings(self):
        dlg = SettingsDialog(self.api_keys, self)
        if dlg.exec_():
            self.api_keys = dlg.get_keys()
            self.models   = dlg.get_models()
            self._rebuild_adapters()

    def _clear_chat(self):
        self.context.clear()
        self.chat_display.clear()
        self.last_target = None
        self._show_welcome()
        self._update_stats()


# ── Entry Point ────────────────────────────────────────────────────────────────
def launch():
    app = QApplication(sys.argv)
    app.setApplicationName("Council")
    app.setStyle("Fusion")

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(BG_DARK))
    palette.setColor(QPalette.WindowText,      QColor(TEXT_MAIN))
    palette.setColor(QPalette.Base,            QColor(BG_INPUT))
    palette.setColor(QPalette.AlternateBase,   QColor(BG_MID))
    palette.setColor(QPalette.Text,            QColor(TEXT_MAIN))
    palette.setColor(QPalette.Button,          QColor(BG_PANEL))
    palette.setColor(QPalette.ButtonText,      QColor(TEXT_MAIN))
    palette.setColor(QPalette.Highlight,       QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#000000"))
    app.setPalette(palette)

    win = CouncilWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    launch()
