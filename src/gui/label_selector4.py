import tkinter as tk
from tkinter import ttk
import os
import sys
import json

WINDOW_WIDTH = 1800
WINDOW_HEIGHT = 600
BUTTON_FONT = ("TkDefaultFont", 12)
BUTTON_WIDTH = 22
BUTTON_HEIGHT = 3
WRAP_LEN = 180

class ToolTip:
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.enabled = True

        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if not self.enabled or self.tip_window or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + cy + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            font=("TkDefaultFont", 10), wraplength=250
        )
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def toggle(self):
        self.enabled = not self.enabled


class LabelSelector:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("Label Selector")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")  # set default size
        self.selected_labels = {cat["name"]: None for cat in self.config['categories']}
        self.buttons = {}
        self.tooltips = []
        self.create_widgets()

    def create_widgets(self):
        self.selected_labels_var = tk.StringVar()
        self.selected_labels_label = ttk.Label(
            self.root, textvariable=self.selected_labels_var, font=("TkDefaultFont", 12, "bold")
        )
        self.selected_labels_label.pack(pady=(10, 5))

        frame = ttk.LabelFrame(self.root, text="Select Labels", padding=(10, 5))
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        for category in self.config['categories']:
            category_frame = ttk.LabelFrame(frame, text=category['name'], padding=(10, 5))
            category_frame.pack(padx=10, pady=8, fill="both", expand=True)

            button_frame = tk.Frame(category_frame)
            button_frame.pack(fill="both", expand=True)

            self.buttons[category['name']] = []
            for col, action in enumerate(category['actions']):
                label = action["label"] if isinstance(action, dict) else action
                desc = action.get("description", "") if isinstance(action, dict) else ""
                btn = tk.Button(
                    button_frame, text=label,
                    font=BUTTON_FONT, width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
                    wraplength=WRAP_LEN,
                    relief="groove", bd=2, bg="lightgrey",
                    command=lambda a=label, c=category['name']: self.on_button_click(a, c)
                )
                btn.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
                button_frame.grid_columnconfigure(col, weight=1)
                self.buttons[category['name']].append(btn)

                if desc:
                    self.tooltips.append(ToolTip(btn, desc))

        # --- Submit row (centered) ---
        submit_frame = tk.Frame(self.root)
        submit_frame.pack(fill="x", pady=(10, 5))
        self.submit_button = ttk.Button(submit_frame, text="Submit", command=self.submit_selections)
        self.submit_button.pack(anchor="center")

        # --- Toggle row (right-aligned below submit) ---
        toggle_frame = tk.Frame(self.root)
        toggle_frame.pack(fill="x", pady=(0, 10), padx=10)
        self.tooltip_button = ttk.Button(toggle_frame, text="Toggle Tooltips", command=self.toggle_tooltips)
        self.tooltip_button.pack(anchor="e")

    def toggle_tooltips(self):
        for tip in self.tooltips:
            tip.toggle()

    def on_button_click(self, label, category):
        self.selected_labels[category] = label
        for btn in self.buttons[category]:
            if btn.cget("text") == label:
                btn.configure(bg="lightgreen")
            else:
                btn.configure(bg="lightgrey")
        self.update_selected_labels_display()

    def update_selected_labels_display(self):
        labels = [f"{k}: {v}" for k, v in self.selected_labels.items() if v]
        self.selected_labels_var.set(" | ".join(labels))
    
    def submit_selections(self):
        decision_string = ", ".join(
            f"{k}: {v}" for k, v in self.selected_labels.items() if v
        )
        output_string = f"decision: [{decision_string}], label: [{decision_string}]"
        self.write_label_and_exit(output_string)
    
    def write_label_and_exit(self, label):
        with open("/tmp/selected_label.txt", "w") as f:
            f.write(label)
        self.root.after(500, lambda: (self.root.destroy(), sys.exit(0)))


def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    with open(os.path.join(os.path.dirname(__file__), 'label_selector_config4.json'), 'r') as f:
        config = json.load(f)
    app = LabelSelector(root, config)
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.mainloop()


if __name__ == "__main__":
    main()
