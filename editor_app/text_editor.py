import tkinter as tk
from tkinter import Text
import re

# --- Syntax Highlighting Definitions ---
SYNTAX_RULES = [ # Ensure this is defined before TextEditor if TextEditor uses it at class level
    ("keyword", r"\b(def|class|if|elif|else|for|while|return|import|from|try|except|finally|with|as|True|False|None|and|or|not|is|in|lambda|global|nonlocal|yield|async|await|pass|break|continue)\b"),
    ("comment", r"#.*"),
    ("string", r"(\".*?\"|\'.*?\')"), # Basic strings, does not cover multi-line strings perfectly yet
    ("multiline_string_double", r"\"\"\".*?\"\"\""),
    ("multiline_string_single", r"\'\'\'.*?\'\'\'"),
]

class TextEditor:
    def __init__(self, master_frame, status_bar, app_instance):
        self.frame = master_frame
        self.status_bar = status_bar # May not be needed if App handles all status updates
        self.app_instance = app_instance # For updating tab text
        self.text_area = Text(self.frame)
        self.text_area.pack(expand=True, fill='both', side='right')
        self.text_area.focus_set()
        self._configure_tags()
        self.is_modified = False

        # Listen for text modifications
        self.text_area.bind("<<Modified>>", self._on_text_modified)
        self.text_area.bind("<KeyRelease>", self.apply_syntax_highlighting) # Keep for syntax highlighting

    def _on_text_modified(self, event=None):
        # This event fires once per modification sequence.
        # Reset the Text widget's modified flag so it fires again next time.
        if self.text_area.edit_modified():
            self.mark_as_modified(True)
            self.text_area.edit_modified(False) # Crucial reset

    def mark_as_modified(self, modified_status):
        self.is_modified = modified_status
        if self.app_instance: # Ensure app_instance is set
            self.app_instance.update_tab_text_for_editor(self, modified_status)

    def _configure_tags(self):
        self.text_area.tag_configure("keyword", foreground="blue")
        self.text_area.tag_configure("comment", foreground="green")
        self.text_area.tag_configure("string", foreground="red")
        self.text_area.tag_configure("multiline_string_double", foreground="red")
        self.text_area.tag_configure("multiline_string_single", foreground="red")
        self.text_area.tag_configure("search_highlight", background="yellow", foreground="black") # New

    def clear_search_highlights(self):
        self.text_area.tag_remove("search_highlight", "1.0", tk.END)

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

    def set_content(self, text_content, initial_load=False):
        current_state = self.text_area.cget("state")
        self.text_area.config(state=tk.NORMAL) # Ensure editable for programmatic change

        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text_content)
        self.apply_syntax_highlighting() # Always highlight after setting content

        if initial_load:
            self.mark_as_modified(False) # Reset modified state and tab text
            self.text_area.edit_reset() # Clears undo/redo stack for new file
            self.text_area.edit_modified(False) # Reset the widget's own modified flag
        else:
            # If not initial_load, it implies a programmatic change that should be considered a modification
            self.mark_as_modified(True)
            # self.text_area.edit_modified(True) # Not needed, <<Modified>> will handle

        self.text_area.config(state=current_state)


    def clear_content(self):
        self.text_area.delete("1.0", tk.END)
