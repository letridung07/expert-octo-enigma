import tkinter as tk

class StatusBar:
    def __init__(self, master_frame):
        self.frame = master_frame
        self.label = tk.Label(self.frame, text="Ready", anchor='w')
        self.label.pack(fill=tk.X)

    def update_status(self, message):
        self.label.config(text=message)

    def update_filepath(self, filepath):
        if filepath:
            self.label.config(text=f"File: {filepath}")
        else:
            self.label.config(text="Ready")
