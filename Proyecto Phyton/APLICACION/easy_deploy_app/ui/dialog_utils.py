# -*- coding: utf-8 -*-
"""Small child-dialog helpers for secondary EASY DEPLOY windows."""

import customtkinter as ctk


def _widget_exists(widget):
    try:
        return bool(widget and widget.winfo_exists())
    except Exception:
        return False


def _child_dialog_registry(parent):
    registry = getattr(parent, "_easydeploy_child_dialogs", None)
    if not isinstance(registry, dict):
        registry = {}
        try:
            setattr(parent, "_easydeploy_child_dialogs", registry)
        except Exception:
            pass
    return registry


def _center_over_parent(dialog, parent, width, height):
    try:
        parent.update_idletasks()
        dialog.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = max(parent.winfo_width(), 1)
        ph = max(parent.winfo_height(), 1)
        x = px + max(0, (pw - width) // 2)
        y = py + max(0, (ph - height) // 2)
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        x = max(12, min(x, max(12, sw - width - 12)))
        y = max(12, min(y, max(12, sh - height - 48)))
    except Exception:
        try:
            sw = dialog.winfo_screenwidth()
            sh = dialog.winfo_screenheight()
            x = max(12, (sw - width) // 2)
            y = max(12, (sh - height) // 2)
        except Exception:
            x = 120
            y = 120
    dialog.geometry(f"{width}x{height}+{x}+{y}")


def _bring_child_dialog_forward(dialog, parent, focus_widget=None, topmost_ms=280):
    def release_topmost():
        try:
            if dialog.winfo_exists():
                dialog.attributes("-topmost", False)
        except Exception:
            pass

    try:
        if dialog.state() in {"iconic", "withdrawn"}:
            dialog.deiconify()
    except Exception:
        try:
            dialog.deiconify()
        except Exception:
            pass
    try:
        dialog.transient(parent)
    except Exception:
        pass
    try:
        dialog.lift(parent)
    except Exception:
        try:
            dialog.lift()
        except Exception:
            pass
    try:
        dialog.attributes("-topmost", True)
        dialog.after(max(120, int(topmost_ms)), release_topmost)
    except Exception:
        release_topmost()
    try:
        (focus_widget or dialog).focus_set()
    except Exception:
        pass


def askyesno_child_dialog(app, parent, title, message, yes_text="Sí", no_text="No", key=None):
    """Show a compact yes/no dialog parented to an existing tool window."""
    if not _widget_exists(parent):
        return False

    dialog_key = key or f"askyesno:{title}"
    registry = _child_dialog_registry(parent)
    existing = registry.get(dialog_key)
    if _widget_exists(existing):
        existing_result = getattr(existing, "_easydeploy_child_result", {"value": False})
        _bring_child_dialog_forward(existing, parent)
        try:
            parent.wait_window(existing)
        except Exception:
            pass
        return bool(existing_result.get("value"))
    registry.pop(dialog_key, None)

    result = {"value": False}
    colors = getattr(app, "colors", {})
    panel_fg = (colors.get("panel_light", "#FFFFFF"), colors.get("panel_dark", "#1F1F22"))
    card_fg = (colors.get("card_light", "#F7F8FA"), colors.get("card_dark", "#26262A"))
    border = (colors.get("border_light", "#D7DAE0"), colors.get("border_dark", "#3A3A40"))
    accent = colors.get("accent", "#2F9E8F")
    accent_hover = colors.get("accent_hover", "#258176")
    secondary = "#6B7280"
    secondary_hover = "#4B5563"

    dialog = ctk.CTkToplevel(parent)
    dialog.withdraw()
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.overrideredirect(False)
    dialog.configure(fg_color=panel_fg)
    dialog._easydeploy_child_result = result
    registry[dialog_key] = dialog

    try:
        dialog.transient(parent)
    except Exception:
        pass

    shell = ctk.CTkFrame(
        dialog,
        fg_color=panel_fg,
        border_width=1,
        border_color=border,
        corner_radius=8,
    )
    shell.pack(fill="both", expand=True, padx=14, pady=14)

    ctk.CTkFrame(shell, height=4, fg_color=accent, corner_radius=3).pack(fill="x", padx=14, pady=(12, 0))

    header = ctk.CTkFrame(shell, fg_color="transparent")
    header.pack(fill="x", padx=18, pady=(16, 8))
    header.grid_columnconfigure(1, weight=1)

    badge = ctk.CTkFrame(header, width=38, height=38, fg_color=card_fg, border_width=1, border_color=border, corner_radius=8)
    badge.grid(row=0, column=0, padx=(0, 10), sticky="n")
    badge.grid_propagate(False)
    ctk.CTkLabel(badge, text="?", font=("Segoe UI", 15, "bold"), text_color=accent).pack(fill="both", expand=True)

    ctk.CTkLabel(
        header,
        text=title,
        font=("Segoe UI", 17, "bold"),
        anchor="w",
        text_color=("gray18", "#F5F5F7"),
    ).grid(row=0, column=1, sticky="ew")

    ctk.CTkLabel(
        shell,
        text=str(message or ""),
        font=("Segoe UI", 13),
        justify="left",
        anchor="nw",
        wraplength=480,
        text_color=("gray25", "gray82"),
    ).pack(fill="x", padx=18, pady=(2, 12))

    buttons = ctk.CTkFrame(shell, fg_color="transparent")
    buttons.pack(fill="x", padx=18, pady=(0, 16))

    def cleanup():
        registry.pop(dialog_key, None)
        try:
            dialog.grab_release()
        except Exception:
            pass

    def finish(value):
        result["value"] = bool(value)
        cleanup()
        try:
            dialog.destroy()
        except Exception:
            pass

    no_button = ctk.CTkButton(
        buttons,
        text=no_text,
        width=132,
        height=40,
        corner_radius=8,
        fg_color=secondary,
        hover_color=secondary_hover,
        font=("Segoe UI", 13, "bold"),
        command=lambda: finish(False),
    )
    no_button.pack(side="right", padx=(8, 0))

    yes_button = ctk.CTkButton(
        buttons,
        text=yes_text,
        width=132,
        height=40,
        corner_radius=8,
        fg_color=accent,
        hover_color=accent_hover,
        font=("Segoe UI", 13, "bold"),
        command=lambda: finish(True),
    )
    yes_button.pack(side="right")

    def close_default(event=None):
        finish(False)

    def on_destroy(event=None):
        if getattr(event, "widget", None) is dialog:
            cleanup()

    dialog.protocol("WM_DELETE_WINDOW", close_default)
    dialog.bind("<Escape>", close_default)
    dialog.bind("<Return>", lambda _event=None: finish(True))
    dialog.bind("<Destroy>", on_destroy, add="+")

    dialog.update_idletasks()
    width = 560
    height = max(230, min(360, shell.winfo_reqheight() + 28))
    _center_over_parent(dialog, parent, width, height)
    dialog.deiconify()
    _bring_child_dialog_forward(dialog, parent, yes_button)
    try:
        dialog.grab_set()
    except Exception:
        pass

    try:
        parent.wait_window(dialog)
    except Exception:
        pass
    return bool(result.get("value"))
