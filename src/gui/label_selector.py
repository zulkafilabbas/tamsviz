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
        self.metadata = {"Customer Number": None, "Customer Sex": None, "Customer Age": None}
        self.buttons = {"Customer Movement": [], "Customer Location": [], "Customer Gaze": [], "Customer Arm Movements": [], "Customer Number": [], "Customer Sex": [], "Customer Age": []}
        self.selected_labels = {"Customer Movement": None, "Customer Location": None, "Customer Gaze": None, "Customer Arm Movements": None, "Customer Number": None, "Customer Sex": None, "Customer Age": None}
        self.create_widgets()

    def create_widgets(self):
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(padx=10, pady=10, fill="both", expand=True)

        # Actions tab
        self.action_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.action_frame, text="Actions")
        self.create_action_widgets(self.action_frame)

        # Metadata tab
        self.metadata_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metadata_frame, text="Metadata")
        self.create_metadata_widgets(self.metadata_frame)

        # Set default tab to Actions
        self.notebook.select(self.action_frame)

        # Selected labels display
        self.selected_labels_frame = ttk.Frame(self.root)
        self.selected_labels_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.selected_labels_var = tk.StringVar()
        self.selected_labels_label = ttk.Label(self.selected_labels_frame, textvariable=self.selected_labels_var)
        self.selected_labels_label.pack()

        # Reset and Submit buttons
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.reset_button = ttk.Button(self.button_frame, text="Reset", command=self.reset_selections)
        self.reset_button.pack(side="left", padx=5)
        self.submit_button = ttk.Button(self.button_frame, text="Submit", command=self.submit_selections)
        self.submit_button.pack(side="left", padx=5)

    def create_metadata_widgets(self, parent):
        # Customer Number buttons
        number_frame = ttk.LabelFrame(parent, text="Customer Number", padding=(10, 5))
        number_frame.pack(padx=10, pady=10, fill="both", expand=True)
        button_frame = ttk.Frame(number_frame)
        button_frame.pack(fill="both", expand=True)
        for i in range(1, 21):
            btn = ttk.Button(button_frame, text=str(i), width=3, command=lambda l=str(i): self.on_button_click(l, "Customer Number"))
            btn.pack(side="left", padx=2, pady=2)
            self.buttons["Customer Number"].append(btn)

        # Customer Sex buttons
        sex_frame = ttk.LabelFrame(parent, text="Customer Sex", padding=(10, 5))
        sex_frame.pack(padx=10, pady=10, fill="both", expand=True)
        for sex in ["Male", "Female"]:
            self.create_button(sex_frame, sex, "Customer Sex")

        # Customer Age buttons
        age_frame = ttk.LabelFrame(parent, text="Customer Age", padding=(10, 5))
        age_frame.pack(padx=10, pady=10, fill="both", expand=True)
        for age in ["Child", "Adult", "Elder"]:
            self.create_button(age_frame, age, "Customer Age")

    def create_action_widgets(self, parent):
        for category in self.config['categories']:
            if category['name'] == "Customer Metadata":
                continue  # Skip metadata category
            frame = ttk.LabelFrame(parent, text=category['name'], padding=(10, 5))
            frame.pack(padx=10, pady=10, fill="both", expand=True)
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill="both", expand=True)
            for action in category['actions']:
                self.create_button(button_frame, action, category['name'])

    def create_button(self, parent, label, category):
        btn = ttk.Button(parent, text=label, command=lambda l=label, c=category: self.on_button_click(l, c))
        btn.pack(side="left", pady=5, padx=5)
        if category in self.buttons:
            self.buttons[category].append(btn)

    def on_button_click(self, label, category):
        if category in self.selected_labels:
            self.selected_labels[category] = label
        self.update_selected_labels_display()

    def update_selected_labels_display(self):
        labels = [f"{k}: {v}" for k, v in self.selected_labels.items() if v]
        self.selected_labels_var.set(", ".join(labels))

    def reset_selections(self):
        self.selected_labels = {key: None for key in self.selected_labels}
        self.update_selected_labels_display()

    def submit_selections(self):
        final_label = ", ".join(f"{k}: {v}" for k, v in self.selected_labels.items() if v)
        
        # if "Customer Movement: Walking" in final_label:
        #     final_label = "Browsing"
        # elif "Customer Movement: Standing" in final_label:
        #     if "Customer Location: Mirror" in final_label and "Customer Gaze: Mirror" in final_label:
        #         final_label = "Mirror"
        #     elif "Customer Location: Shelf" in final_label and "Customer Gaze: Shelf" in final_label:
        #         final_label = "Shelf"
        #     elif "Customer Location: Checkout" in final_label and "Customer Gaze: Checkout" in final_label:
        #         final_label = "Purchasing"
        #     elif "Customer Location: Isle" in final_label and "Customer Gaze: Isle" in final_label:
        #         final_label = "Isle"
        #     else:
        #         final_label = "Idle"
        # elif "Customer Arm Movements:" in final_label:
        #     if "Customer Arm Movements: Picking" in final_label:
        #         final_label = "Picking"
        #     elif "Customer Arm Movements: Holding" in final_label:
        #         final_label = "Holding"
        #     elif "Customer Arm Movements: Wearing" in final_label:
        #         final_label = "Wearing"
        #     elif "Customer Arm Movements: Idle" in final_label:
        #         final_label = "Idle"
        #     else:
        #         final_label = "Other Arm Movement"

        self.write_label_and_exit(final_label)

    def write_label_and_exit(self, label):
        with open("/tmp/selected_label.txt", "w") as f:
            f.write(label)
        self.root.after(500, lambda: (self.root.destroy(), sys.exit(-1)))

def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    with open(os.path.join(os.path.dirname(__file__), 'label_selector_config.json'), 'r') as f:
        config = json.load(f)
    app = LabelSelector(root, config)
    root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(-1))
    root.mainloop()

if __name__ == "__main__":
    main()
    sys.exit(-1)