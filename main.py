# Import the Tkinter library
import tkinter as tk
from tkinter import Text, filedialog, Menu, ttk
import os
import re

# --- Syntax Highlighting Definitions ---
SYNTAX_RULES = [
    ("keyword", r"\b(def|class|if|elif|else|for|while|return|import|from|try|except|finally|with|as|True|False|None|and|or|not|is|in|lambda|global|nonlocal|yield|async|await|pass|break|continue)\b"),
    ("comment", r"#.*"),
    ("string", r"(\".*?\"|\'.*?\')"), # Basic strings, does not cover multi-line strings perfectly yet
    ("multiline_string_double", r"\"\"\".*?\"\"\""),
    ("multiline_string_single", r"\'\'\'.*?\'\'\'"),
]

class TextEditor:
    def __init__(self, master_frame, status_bar):
        self.frame = master_frame
        self.status_bar = status_bar
        self.text_area = Text(self.frame)
        self.text_area.pack(expand=True, fill='both', side='right')
        self.text_area.focus_set()
        self._configure_tags()
        self.text_area.bind("<KeyRelease>", self.apply_syntax_highlighting)
        # Could add scrollbars here if needed

    def _configure_tags(self):
        self.text_area.tag_configure("keyword", foreground="blue")
        self.text_area.tag_configure("comment", foreground="green")
        self.text_area.tag_configure("string", foreground="red")
        self.text_area.tag_configure("multiline_string_double", foreground="red")
        self.text_area.tag_configure("multiline_string_single", foreground="red")

    def apply_syntax_highlighting(self, event=None):
        content = self.get_content()
        # Remove existing tags first
        for tag, _ in SYNTAX_RULES:
            self.text_area.tag_remove(tag, "1.0", tk.END)
        
        # Apply new tags
        for tag, pattern in SYNTAX_RULES:
            for match in re.finditer(pattern, content, re.MULTILINE if tag.startswith("multiline") else 0):
                start_index = self.text_area.index(f"1.0 + {match.start()} chars")
                end_index = self.text_area.index(f"1.0 + {match.end()} chars")
                self.text_area.tag_add(tag, start_index, end_index)

    def get_content(self):
        return self.text_area.get("1.0", tk.END)

    def set_content(self, text_content, apply_highlighting=True):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text_content)
        if apply_highlighting:
            self.apply_syntax_highlighting()

    def clear_content(self):
        self.text_area.delete("1.0", tk.END)

class FileExplorer:
    def __init__(self, master_frame, text_editor_instance, app_instance):
        self.frame = master_frame
        self.text_editor = text_editor_instance
        self.app = app_instance # To call update_title_and_status

        self.file_tree = ttk.Treeview(self.frame)
        self.file_tree.pack(expand=True, fill='both')
        self.file_tree["columns"] = ("path",)
        self.file_tree.heading("#0", text="Name", anchor="w")
        self.file_tree.column("#0", anchor="w")
        self.file_tree.column("path", width=0, stretch=tk.NO) # Hide path column

        self.populate_file_explorer(os.getcwd())
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_select)

    def populate_file_explorer(self, path):
        # Clear existing items first
        for i in self.file_tree.get_children():
            self.file_tree.delete(i)
        # Populate with new items
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            self.file_tree.insert('', 'end', text=item, values=[item_path])
            # TODO: Add recursion for directories

    def _on_file_select(self, event=None):
        selected_item = self.file_tree.selection()
        if selected_item:
            item_values = self.file_tree.item(selected_item, "values")
            if item_values:
                filepath = item_values[0]
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r") as input_file:
                            text_content = input_file.read()
                        self.text_editor.set_content(text_content)
                        self.app.update_title_and_status(filepath)
                    except Exception as e:
                        print(f"Error opening file from explorer: {e}")
                        self.app.status_bar.update_status(f"Error opening: {os.path.basename(filepath)}")


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


class App:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Basic Text Editor - Refactored")

        # --- Main Content Frame ---
        # This frame will hold File Explorer (left) and TextEditor (right)
        main_content_frame = tk.Frame(self.window)
        main_content_frame.pack(expand=True, fill='both', side=tk.TOP) # Changed side

        # --- Status Bar ---
        # Status bar should be created before TextEditor if TextEditor needs it
        status_bar_frame = tk.Frame(self.window, relief=tk.SUNKEN, bd=1)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar = StatusBar(status_bar_frame)

        # --- File Explorer ---
        # Takes a portion of the main_content_frame
        file_explorer_frame = tk.Frame(main_content_frame, width=250) # Increased default width
        file_explorer_frame.pack(side='left', fill='y', expand=False)
        file_explorer_frame.pack_propagate(False)

        # --- Text Editor ---
        # Takes the remaining space in main_content_frame
        text_editor_frame = tk.Frame(main_content_frame) # Parent is main_content_frame
        text_editor_frame.pack(expand=True, fill='both', side='right')
        self.text_editor = TextEditor(text_editor_frame, self.status_bar)
        
        # Now initialize FileExplorer, passing the App instance for callbacks
        self.file_explorer = FileExplorer(file_explorer_frame, self.text_editor, self)


        self._create_menu()

    def _create_menu(self):
        self.menubar = Menu(self.window)
        self.window.config(menu=self.menubar)

        file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.quit)

    def open_file(self):
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("Text Files", "*.txt"), ("Python Files", "*.py"), ("Markdown Files", "*.md"), ("All Files", "*.*")]
            )
            if not filepath:
                return
            
            with open(filepath, "r") as input_file:
                text_content = input_file.read()

            self.text_editor.set_content(text_content)
            self.update_title_and_status(filepath)
        except Exception as e:
            print(f"An error occurred while opening the file: {e}")
            self.status_bar.update_status(f"Error opening file: {os.path.basename(filepath)}")

    def save_file(self):
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("Python Files", "*.py"), ("Markdown Files", "*.md"), ("All Files", "*.*")]
            )
            if not filepath:
                return

            text_content = self.text_editor.get_content()
            with open(filepath, "w") as output_file:
                output_file.write(text_content)
            self.update_title_and_status(filepath)
        except Exception as e:
            print(f"An error occurred while saving the file: {e}")
            self.status_bar.update_status("Error saving file.")

    def update_title_and_status(self, filepath=None):
        if filepath:
            self.window.title(f"Basic Text Editor - {filepath}")
            self.status_bar.update_filepath(filepath)
        else:
            self.window.title("Basic Text Editor - Refactored")
            self.status_bar.update_status("Ready")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()
