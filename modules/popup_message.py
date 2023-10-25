import tkinter as tk


def initialize_popup(self):
    self.popup = None


def show_popup(self, message, y_offset=30):
    if self.popup:
        self.popup.destroy()
    x, y = self.winfo_pointerxy()
    self.popup = tk.Toplevel(self)
    self.popup.overrideredirect(True)
    label = tk.Label(self.popup, text=message)
    label.pack()
    self.popup.wm_geometry("+%d+%d" % (x, y - y_offset))
    self.popup.after(20, lambda: modify_popup_location(self, y_offset))


def modify_popup_location(self, y_offset):
    x, y = self.winfo_pointerxy()
    if self.popup:
        self.popup.wm_geometry("+%d+%d" % (x, y - y_offset))
        self.popup.after(20, lambda: modify_popup_location(self, y_offset))


def hide_popup(self):
    if self.popup:
        self.popup.destroy()
