# -*- coding: utf-8 -*-
"""
PySide6 Compatibility Layer for Tkinter API
============================================
This module provides drop-in replacements for common tkinter patterns using
PySide6 as the backend. Import this module and use `tk` and `ttk` namespaces
exactly as you would with tkinter.

Usage:
    from pyside6_compat import tk, ttk, filedialog, messagebox, scrolledtext
"""
import os as _os
import sys as _sys

# Fix Windows DLL search order for PySide6 and MKL / LAPACK under Conda
if _sys.platform == "win32":
    import ctypes as _ctypes
    _sys32_icu = _os.path.join(_os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icuuc.dll")
    if _os.path.exists(_sys32_icu):
        try:
            _ctypes.WinDLL(_sys32_icu)
        except Exception:
            pass

    _lib_bin = _os.path.join(_sys.prefix, "Library", "bin")
    if _os.path.isdir(_lib_bin):
        if _lib_bin not in _os.environ.get("PATH", ""):
            _os.environ["PATH"] = _lib_bin + _os.pathsep + _os.environ.get("PATH", "")
        if hasattr(_os, "add_dll_directory"):
            try:
                _os.add_dll_directory(_lib_bin)
            except Exception:
                pass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QRadioButton,
    QGroupBox, QScrollArea, QFrame, QMessageBox, QComboBox, QTextEdit,
    QButtonGroup, QStackedWidget, QSizePolicy, QFileDialog,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor


def _parse_font(font_spec):
    """Convert tkinter font spec to QFont."""
    if isinstance(font_spec, tuple):
        family = font_spec[0] if len(font_spec) > 0 else "Calibri"
        size = int(font_spec[1]) if len(font_spec) > 1 else 10
        bold = len(font_spec) > 2 and "bold" in str(font_spec[2]).lower()
        f = QFont(family, size)
        if bold:
            f.setBold(True)
        return f
    elif isinstance(font_spec, str):
        parts = font_spec.split()
        family = parts[0] if parts else "Calibri"
        size = 10
        bold = False
        for p in parts[1:]:
            if p.isdigit():
                size = int(p)
            elif p.lower() == "bold":
                bold = True
        f = QFont(family, size)
        if bold:
            f.setBold(True)
        return f
    return QFont("Calibri", 10)


def _get_parent(w):
    """Safely obtain parent widget without conflicting with shadowed .parent attributes."""
    p = getattr(w, "_tk_parent", None)
    if p is not None:
        return p
    p_attr = getattr(w, "parent", None)
    if callable(p_attr):
        try:
            return p_attr()
        except TypeError:
            pass
    elif p_attr is not None:
        return p_attr
    if isinstance(w, QWidget):
        return QWidget.parent(w)
    return None


class _TkRoot(QMainWindow):
    """Compatibility wrapper for tk.Tk and tk.Toplevel -> QMainWindow."""
    _qapp = None

    def __init__(self, *args, **kw):
        if _TkRoot._qapp is None:
            _TkRoot._qapp = QApplication.instance() or QApplication(_sys.argv)
        super().__init__()
        self._tk_parent = None

    @staticmethod
    def wm_title(instance, title):
        instance.setWindowTitle(title)

    def winfo_screenwidth(self):
        screen = _TkRoot._qapp.primaryScreen()
        return screen.size().width() if screen else 1920

    def winfo_screenheight(self):
        screen = _TkRoot._qapp.primaryScreen()
        return screen.size().height() if screen else 1080

    def geometry(self, geom_str):
        import re as _re
        m = _re.match(r'(\d+)x(\d+)\+?(-?\d+)?\+?(-?\d+)?', geom_str)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            self.resize(w, h)
            if m.group(3) and m.group(4):
                self.move(int(m.group(3)), int(m.group(4)))

    def minsize(self, w, h):
        self.setMinimumSize(w, h)

    def maxsize(self, w, h):
        self.setMaximumSize(w, h)

    def state(self, s):
        if s == "zoomed":
            self.showMaximized()

    def title(self, t):
        self.setWindowTitle(t)

    def attributes(self, *args):
        pass

    def resizable(self, w, h):
        if not w and not h:
            self.setFixedSize(self.size())

    def grid_rowconfigure(self, *args, **kw):
        pass

    def grid_columnconfigure(self, *args, **kw):
        pass

    def rowconfigure(self, *args, **kw):
        pass

    def columnconfigure(self, *args, **kw):
        pass

    def protocol(self, name, func):
        pass

    def bind(self, *args, **kw):
        pass

    def focus_set(self):
        self.setFocus()

    def winfo_children(self):
        return self.findChildren(QWidget)

    def winfo_toplevel(self):
        return self

    def configure(self, **kw):
        pass

    def config(self, **kw):
        pass

    def update(self):
        QApplication.processEvents()

    def update_idletasks(self):
        QApplication.processEvents()

    def mainloop(self):
        self.show()
        if _TkRoot._qapp:
            _TkRoot._qapp.exec()

    def quit(self):
        self.close()
        if _TkRoot._qapp:
            _TkRoot._qapp.quit()

    def destroy(self):
        self.close()
        if _TkRoot._qapp:
            _TkRoot._qapp.quit()


def _compat_place(widget, x=0, y=0, width=None, height=None, relx=0, rely=0, anchor="", **kw):
    p = _get_parent(widget)
    if p and widget.parent() != p:
        widget.setParent(p)
    px = int(x) if x is not None else 0
    py = int(y) if y is not None else 0
    if relx and p:
        px += int(relx * max(1, p.width()))
    if rely and p:
        py += int(rely * max(1, p.height()))
    hint = widget.sizeHint()
    w = int(width) if width is not None else max(hint.width(), 40)
    h = int(height) if height is not None else max(hint.height(), 24)
    widget.setGeometry(px, py, max(w, 10), max(h, 10))
    widget.show()


class _TkCompat:
    """Namespace providing tkinter-compatible widget constructors backed by PySide6."""
    END = "end"
    BOTH = "both"
    X = "x"
    Y = "y"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    DISABLED = "disabled"
    NORMAL = "normal"
    W = "w"
    E = "e"
    N = "n"
    S = "s"

    Tk = _TkRoot
    Toplevel = _TkRoot
    class Frame(QFrame):
        """Compatibility wrapper for tk.Frame."""
        def __init__(self, parent=None, bg=None, **kw):
            super().__init__(parent)
            self._tk_parent = parent
            if bg and bg != "SystemButtonFace":
                self.setStyleSheet(f"background-color: {bg};")
            self._grid_layout = QGridLayout(self)
            self._grid_layout.setContentsMargins(2, 2, 2, 2)
            self._grid_layout.setSpacing(2)

        def columnconfigure(self, col, weight=0, **kw):
            self._grid_layout.setColumnStretch(col, weight)

        def grid_columnconfigure(self, col, weight=0, **kw):
            self._grid_layout.setColumnStretch(col, weight)

        def grid_rowconfigure(self, row, weight=0, **kw):
            self._grid_layout.setRowStretch(row, weight)

        def rowconfigure(self, row, weight=0, **kw):
            self._grid_layout.setRowStretch(row, weight)

        def winfo_children(self):
            return self.findChildren(QWidget)

        def winfo_toplevel(self):
            return self.window()

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan)
            elif p and hasattr(p, '_stack'):
                p._stack.addWidget(self)

        def pack(self, side="top", padx=0, pady=0, fill="", expand=False,
                 ipadx=0, ipady=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0, 1, max(1, p._grid_layout.columnCount()))

        def place(self, x=0, y=0, width=None, height=None, relx=0, rely=0, anchor="", **kw):
            _compat_place(self, x=x, y=y, width=width, height=height, relx=relx, rely=rely, anchor=anchor, **kw)

        def tkraise(self):
            p = _get_parent(self)
            if p and hasattr(p, '_stack'):
                p._stack.setCurrentWidget(self)
            self.raise_()

        def configure(self, **kw):
            pass

        def config(self, **kw):
            pass

        def update_idletasks(self):
            QApplication.processEvents()

        def bind(self, *args, **kw):
            pass

        def unbind(self, *args, **kw):
            pass

    class LabelFrame(QGroupBox):
        """Compatibility wrapper for tk.LabelFrame."""
        def __init__(self, parent=None, text="", font=None, fg=None, padx=0, pady=0, **kw):
            super().__init__(text, parent)
            self._tk_parent = parent
            if font:
                self.setFont(_parse_font(font))
            if fg:
                self.setStyleSheet(f"QGroupBox {{ color: {fg}; }}")
            self._grid_layout = QGridLayout(self)
            self._grid_layout.setContentsMargins(padx+5, pady+15, padx+5, pady+5)
            self._grid_layout.setSpacing(4)

        def columnconfigure(self, col, weight=0, **kw):
            self._grid_layout.setColumnStretch(col, weight)

        def grid_columnconfigure(self, col, weight=0, **kw):
            self._grid_layout.setColumnStretch(col, weight)

        def grid_rowconfigure(self, row, weight=0, **kw):
            self._grid_layout.setRowStretch(row, weight)

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan)

        def pack(self, side="top", padx=0, pady=0, fill="", expand=False, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0, 1, max(1, p._grid_layout.columnCount()))

        def configure(self, **kw):
            pass

        def config(self, **kw):
            pass

    class Label(QLabel):
        """Compatibility wrapper for tk.Label."""
        def __init__(self, parent=None, text="", font=None, fg=None, foreground=None,
                     anchor=None, justify=None, wraplength=None, background=None, **kw):
            super().__init__(str(text) if text is not None else "", parent)
            self._tk_parent = parent
            color = fg or foreground
            if font:
                self.setFont(_parse_font(font))
            if color:
                self.setStyleSheet(f"color: {color};")
            if anchor == "w":
                self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            elif anchor == "center":
                self.setAlignment(Qt.AlignCenter)
            if wraplength:
                self.setWordWrap(True)
                self.setMaximumWidth(wraplength)

        def __setitem__(self, key, value):
            if key == "text":
                self.setText(str(value))
            elif key in ("fg", "foreground"):
                self.setStyleSheet(f"color: {value};")

        def __getitem__(self, key):
            if key == "text":
                return self.text()
            return ""

        def configure(self, **kw):
            if "text" in kw:
                self.setText(str(kw["text"]))
            if "fg" in kw or "foreground" in kw:
                c = kw.get("fg") or kw.get("foreground")
                self.setStyleSheet(f"color: {c};")

        def config(self, **kw):
            self.configure(**kw)

        def cget(self, key):
            return self[key]

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                alignment = Qt.Alignment()
                if "w" in sticky and "e" not in sticky:
                    alignment = Qt.AlignLeft | Qt.AlignVCenter
                elif "e" in sticky and "w" not in sticky:
                    alignment = Qt.AlignRight | Qt.AlignVCenter
                elif "center" in sticky:
                    alignment = Qt.AlignCenter
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan, alignment)

        def pack(self, side="top", padx=0, pady=0, fill="", expand=False, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0, 1, max(1, p._grid_layout.columnCount()))

        def place(self, x=0, y=0, width=None, height=None, relx=0, rely=0, anchor="", **kw):
            _compat_place(self, x=x, y=y, width=width, height=height, relx=relx, rely=rely, anchor=anchor, **kw)

        def bind(self, *args, **kw):
            pass

    class Button(QPushButton):
        """Compatibility wrapper for tk.Button."""
        def __init__(self, parent=None, text="", command=None, font=None,
                     fg=None, bg=None, width=None, height=None, **kw):
            super().__init__(str(text), parent)
            self._tk_parent = parent
            if command:
                self.clicked.connect(command)
            if font:
                self.setFont(_parse_font(font))
            style = []
            if fg:
                style.append(f"color: {fg};")
            if bg and bg != "SystemButtonFace":
                style.append(f"background-color: {bg};")
            if style:
                self.setStyleSheet(" ".join(style))
            if width:
                self.setMinimumWidth(width * 8)
            if height:
                self.setMinimumHeight(height * 20)

        def configure(self, **kw):
            if "text" in kw:
                self.setText(str(kw["text"]))
            if "command" in kw:
                try:
                    self.clicked.disconnect()
                except Exception:
                    pass
                self.clicked.connect(kw["command"])
            if "state" in kw:
                self.setEnabled(kw["state"] != "disabled")

        def config(self, **kw):
            self.configure(**kw)

        def __setitem__(self, key, value):
            self.configure(**{key: value})

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan)

        def pack(self, side="top", padx=0, pady=0, fill="", expand=False, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0, 1, max(1, p._grid_layout.columnCount()))

        def place(self, x=0, y=0, width=None, height=None, relx=0, rely=0, anchor="", **kw):
            _compat_place(self, x=x, y=y, width=width, height=height, relx=relx, rely=rely, anchor=anchor, **kw)

    class Entry(QLineEdit):
        """Compatibility wrapper for tk.Entry."""
        def __init__(self, parent=None, textvariable=None, width=None, font=None,
                     justify=None, state=None, **kw):
            super().__init__(parent)
            self._tk_parent = parent
            self._var = textvariable
            if textvariable is not None:
                self.setText(str(textvariable.get()))
                self.textChanged.connect(lambda t: textvariable.set(t))
            if width:
                self.setFixedWidth(width * 9)
            if font:
                self.setFont(_parse_font(font))
            if justify == "center":
                self.setAlignment(Qt.AlignCenter)
            elif justify == "right":
                self.setAlignment(Qt.AlignRight)
            if state == "disabled" or state == "readonly":
                self.setReadOnly(True)

        def get(self):
            return self.text()

        def delete(self, first, last=None):
            if first == 0 and (last == "end" or last is None):
                self.clear()
            else:
                current = self.text()
                end_idx = len(current) if last == "end" else int(last)
                self.setText(current[:int(first)] + current[end_idx:])

        def insert(self, index, string):
            if index == 0:
                self.setText(str(string) + self.text())
            elif index == "end":
                self.setText(self.text() + str(string))
            else:
                idx = int(index)
                t = self.text()
                self.setText(t[:idx] + str(string) + t[idx:])

        def configure(self, **kw):
            if "state" in kw:
                self.setReadOnly(kw["state"] in ("disabled", "readonly"))

        def config(self, **kw):
            self.configure(**kw)

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan)

        def pack(self, side="top", padx=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0)

        def bind(self, *args, **kw):
            pass

    class Checkbutton(QCheckBox):
        """Compatibility wrapper for tk.Checkbutton."""
        def __init__(self, parent=None, text="", variable=None, command=None,
                     onvalue=1, offvalue=0, font=None, **kw):
            super().__init__(str(text), parent)
            self._tk_parent = parent
            self._variable = variable
            self._onvalue = onvalue
            self._offvalue = offvalue
            if variable is not None:
                val = variable.get()
                self.setChecked(val == onvalue)
                self.toggled.connect(
                    lambda checked: variable.set(self._onvalue if checked else self._offvalue)
                )
            if command:
                self.clicked.connect(command)
            if font:
                self.setFont(_parse_font(font))

        def select(self):
            self.setChecked(True)

        def deselect(self):
            self.setChecked(False)

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                alignment = Qt.AlignLeft if "w" in sticky else Qt.Alignment()
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan, alignment)

        def pack(self, side="top", padx=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0)

        def place(self, x=0, y=0, width=None, height=None, relx=0, rely=0, anchor="", **kw):
            _compat_place(self, x=x, y=y, width=width, height=height, relx=relx, rely=rely, anchor=anchor, **kw)

    class Radiobutton(QRadioButton):
        """Compatibility wrapper for tk.Radiobutton."""
        def __init__(self, parent=None, text="", variable=None, value=None,
                     command=None, font=None, **kw):
            super().__init__(str(text), parent)
            self._tk_parent = parent
            self._variable = variable
            self._value = value
            if font:
                self.setFont(_parse_font(font))
            if variable is not None and value is not None:
                if variable.get() == value:
                    self.setChecked(True)
                def on_toggled(checked):
                    if checked and variable is not None:
                        variable.set(value)
                    if checked and command:
                        command()
                self.toggled.connect(on_toggled)

        def select(self):
            self.setChecked(True)

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                alignment = Qt.AlignLeft if "w" in sticky else Qt.Alignment()
                p._grid_layout.addWidget(self, row, column, alignment)

        def pack(self, side="top", padx=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0)

        def place(self, x=0, y=0, width=None, height=None, relx=0, rely=0, anchor="", **kw):
            _compat_place(self, x=x, y=y, width=width, height=height, relx=relx, rely=rely, anchor=anchor, **kw)

    class IntVar:
        """Compatibility wrapper for tk.IntVar."""
        def __init__(self, master=None, value=0, **kw):
            self._value = int(value)
            self._callbacks = []

        def get(self):
            return self._value

        def set(self, value):
            self._value = int(value)
            for cb in self._callbacks:
                try:
                    cb()
                except Exception:
                    pass

        def trace(self, mode, callback):
            self._callbacks.append(callback)

    class StringVar:
        """Compatibility wrapper for tk.StringVar."""
        def __init__(self, master=None, value="", **kw):
            self._value = str(value)
            self._callbacks = []

        def get(self):
            return self._value

        def set(self, value):
            self._value = str(value)
            for cb in self._callbacks:
                try:
                    cb()
                except Exception:
                    pass

        def trace(self, mode, callback):
            self._callbacks.append(callback)

    class DoubleVar:
        """Compatibility wrapper for tk.DoubleVar."""
        def __init__(self, master=None, value=0.0, **kw):
            self._value = float(value)

        def get(self):
            return self._value

        def set(self, value):
            self._value = float(value)

    class BooleanVar:
        """Compatibility wrapper for tk.BooleanVar."""
        def __init__(self, master=None, value=False, **kw):
            self._value = bool(value)

        def get(self):
            return self._value

        def set(self, value):
            self._value = bool(value)

    class OptionMenu(QComboBox):
        """Compatibility wrapper for tk.OptionMenu."""
        def __init__(self, parent, variable, *options, **kw):
            super().__init__(parent)
            self._tk_parent = parent
            self._variable = variable
            for opt in options:
                self.addItem(str(opt))
            idx = self.findText(str(variable._value if hasattr(variable, '_value') else variable.get()))
            if idx >= 0:
                self.setCurrentIndex(idx)
            self.currentTextChanged.connect(lambda text: variable.set(text))

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column)

        def pack(self, side="top", padx=0, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0)

    class Text(QTextEdit):
        """Compatibility wrapper for tk.Text."""
        def __init__(self, parent=None, height=3, state=None, fg=None, bg=None, **kw):
            super().__init__(parent)
            self._tk_parent = parent
            self.setMaximumHeight(height * 20)
            if state == "disabled":
                self.setReadOnly(True)
            style = ""
            if fg:
                style += f"color: {fg};"
            if bg:
                style += f"background-color: {bg};"
            if style:
                self.setStyleSheet(style)

        def insert(self, pos, text):
            self.append(str(text))

        def delete(self, first, last=None):
            self.clear()

        def get(self, first="1.0", last="end"):
            return self.toPlainText()

        def see(self, index):
            cursor = self.textCursor()
            cursor.movePosition(cursor.End)
            self.setTextCursor(cursor)

        def configure(self, **kw):
            if "state" in kw:
                self.setReadOnly(kw["state"] == "disabled")

        def config(self, **kw):
            self.configure(**kw)

        def grid(self, row=0, column=0, sticky="", padx=0, pady=0,
                 columnspan=1, rowspan=1, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column, rowspan, columnspan)

        def pack(self, side="top", padx=0, pady=0, fill="", expand=False, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0, 1, max(1, p._grid_layout.columnCount()))

        def yview(self, *args):
            pass

    class Canvas(QFrame):
        """Minimal compatibility wrapper for tk.Canvas."""
        def __init__(self, parent=None, bg=None, highlightthickness=0, **kw):
            super().__init__(parent)
            self._tk_parent = parent
            self._grid_layout = QGridLayout(self)
            self._grid_layout.setContentsMargins(0, 0, 0, 0)

        def create_window(self, pos, window=None, **kw):
            if window and hasattr(self, '_grid_layout'):
                self._grid_layout.addWidget(window, 0, 0)
            return 0

        def itemconfig(self, *args, **kw):
            pass

        def configure(self, **kw):
            pass

        def config(self, **kw):
            pass

        def bbox(self, *args):
            return (0, 0, 100, 100)

        def yview(self, *args):
            pass

        def xview(self, *args):
            pass

        def yview_scroll(self, *args, **kw):
            pass

        def bind_all(self, *args, **kw):
            pass

        def unbind_all(self, *args, **kw):
            pass

        def bind(self, *args, **kw):
            pass

        def grid(self, row=0, column=0, sticky="", **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                p._grid_layout.addWidget(self, row, column)

        def pack(self, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0)

    class Scrollbar(QFrame):
        """No-op: PySide6 layouts handle scrolling."""
        def __init__(self, parent=None, orient=None, command=None, **kw):
            super().__init__(parent)
            self._tk_parent = parent
            self.hide()

        def set(self, *args):
            pass

        def grid(self, **kw):
            pass

        def pack(self, **kw):
            pass

    class Separator(QFrame):
        """Compatibility wrapper for ttk.Separator."""
        def __init__(self, parent=None, orient="horizontal", **kw):
            super().__init__(parent)
            self._tk_parent = parent
            if orient == "horizontal":
                self.setFrameShape(QFrame.HLine)
            else:
                self.setFrameShape(QFrame.VLine)
            self.setStyleSheet("color: #d0d0d0;")

        def pack(self, fill="", **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0, 1, max(1, p._grid_layout.columnCount()))

        def grid(self, **kw):
            p = _get_parent(self)
            if p and hasattr(p, '_grid_layout'):
                row = p._grid_layout.rowCount()
                p._grid_layout.addWidget(self, row, 0)

    class Style:
        """No-op compatibility for ttk.Style."""
        def theme_use(self, *args):
            pass

        def configure(self, *args, **kw):
            pass


class _filedialog:
    """Compatibility wrapper for tkinter.filedialog."""
    @staticmethod
    def askopenfilename(**kw):
        fname, _ = QFileDialog.getOpenFileName(None, "Open File")
        return fname

    @staticmethod
    def asksaveasfilename(**kw):
        fname, _ = QFileDialog.getSaveFileName(None, "Save File")
        return fname


class _messagebox:
    """Compatibility wrapper for tkinter.messagebox."""
    @staticmethod
    def showinfo(title="", message=""):
        QMessageBox.information(None, title, message)

    @staticmethod
    def showerror(title="", message=""):
        QMessageBox.critical(None, title, message)

    @staticmethod
    def showwarning(title="", message=""):
        QMessageBox.warning(None, title, message)

    @staticmethod
    def askyesno(title="", message=""):
        result = QMessageBox.question(None, title, message,
                                       QMessageBox.Yes | QMessageBox.No)
        return result == QMessageBox.Yes


class _scrolledtext:
    """Compatibility wrapper for tkinter.scrolledtext."""
    ScrolledText = _TkCompat.Text


# Public API
tk = _TkCompat
ttk = _TkCompat
filedialog = _filedialog
messagebox = _messagebox
scrolledtext = _scrolledtext
