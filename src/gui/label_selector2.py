import tkinter as tk
from tkinter import ttk
import os
import sys
import json

class LabelSelector:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("Label Selector")
        self.selected_labels = {"Movement & Location": None, "Arm Action": None}
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.LabelFrame(self.root, text="Select Labels", padding=(10, 5))
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        for category in self.config['categories']:
            category_frame = ttk.LabelFrame(frame, text=category['name'], padding=(10, 5))
            category_frame.pack(padx=10, pady=5, fill="both", expand=True)
            
            button_frame = ttk.Frame(category_frame)
            button_frame.pack(fill="both", expand=True)
            
            for action in category['actions']:
                self.create_button(button_frame, action, category['name'])
        
        self.selected_labels_var = tk.StringVar()
        self.selected_labels_label = ttk.Label(self.root, textvariable=self.selected_labels_var)
        self.selected_labels_label.pack(pady=10)
        
        self.submit_button = ttk.Button(self.root, text="Submit", command=self.submit_selections)
        self.submit_button.pack(pady=5)

    def create_button(self, parent, label, category):
        btn = ttk.Button(parent, text=label, command=lambda: self.on_button_click(label, category))
        btn.pack(side="left", padx=5, pady=5)
    
    def on_button_click(self, label, category):
        self.selected_labels[category] = label
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
    with open(os.path.join(os.path.dirname(__file__), 'label_selector_config2.json'), 'r') as f:
        config = json.load(f)
    app = LabelSelector(root, config)
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.mainloop()


if __name__ == "__main__":
    main()
