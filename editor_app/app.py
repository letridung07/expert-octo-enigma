import tkinter as tk
from tkinter import filedialog, Menu, ttk, messagebox, simpledialog
import os
from .text_editor import TextEditor, SYNTAX_RULES
from .file_explorer import FileExplorer
from .status_bar import StatusBar

class App:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Basic Text Editor - Refactored")

        self.case_sensitive_var = tk.BooleanVar()
        # self.regex_var = tk.BooleanVar() # For later

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

        # --- Notebook for Tabbed Editing ---
        self.notebook = ttk.Notebook(main_content_frame)
        self.notebook.pack(expand=True, fill='both', side='right')
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed) # Step 5

        # Store TextEditor instances and their filepaths
        self.editors = {}  # Maps tab_id (widget path) to TextEditor instance
        self.tab_filepaths = {}  # Maps tab_id (widget path) to filepath

        # --- File Explorer ---
        file_explorer_frame = tk.Frame(main_content_frame, width=250)
        file_explorer_frame.pack(side='left', fill='y', expand=False)
        file_explorer_frame.pack_propagate(False)
        # FileExplorer now gets 'self' (App instance) to call back for opening files
        self.file_explorer = FileExplorer(file_explorer_frame, self, self)

        self._create_menu()
        self.update_title_and_status() # Initial status update for empty notebook

    def _create_menu(self):
        self.menubar = Menu(self.window)
        self.window.config(menu=self.menubar)

        # File Menu
        file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Close Tab", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_application)

        # Edit Menu
        edit_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find", command=self._toggle_search_frame)

        self._setup_search_ui() # Call new method to initialize search UI components

    def _setup_search_ui(self):
        self.search_frame_visible = False
        self.search_frame = tk.Frame(self.window, height=30) # Give it a nominal height
        # Widgets are created here but search_frame is packed by _toggle_search_frame

        tk.Label(self.search_frame, text="Find:").pack(side=tk.LEFT, padx=(5,2))
        self.search_entry = tk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.search_entry.bind("<Return>", self._find_next)
        self.search_entry.bind("<Shift-Return>", self._find_previous)

        self.find_next_button = tk.Button(self.search_frame, text="Next", command=self._find_next, width=8)
        self.find_next_button.pack(side=tk.LEFT, padx=2)
        self.find_prev_button = tk.Button(self.search_frame, text="Previous", command=self._find_previous, width=8)
        self.find_prev_button.pack(side=tk.LEFT, padx=2)

        self.case_sensitive_check = tk.Checkbutton(
            self.search_frame, text="Case Sensitive", variable=self.case_sensitive_var,
            command=self._on_search_option_changed
        )
        self.case_sensitive_check.pack(side=tk.LEFT, padx=2)

        # self.regex_check = tk.Checkbutton(self.search_frame, text="Regex", variable=self.regex_var, command=self._on_search_option_changed)
        # self.regex_check.pack(side=tk.LEFT, padx=2) # For later

        self.close_search_button = tk.Button(self.search_frame, text="X", command=self._toggle_search_frame, width=3)
        self.close_search_button.pack(side=tk.LEFT, padx=(2,5))

        self.last_search_match_info = {'index': "1.0", 'query': ""}

    def _on_search_option_changed(self):
        # When a search option (like case sensitivity) changes, reset the last match info
        # so the next search starts fresh.
        self.last_search_match_info = {'index': "1.0", 'query': self.search_entry.get()}
        # Optionally, could re-trigger find_next if query exists, but for now, just reset.
        editor = self.get_current_editor()
        if editor:
            editor.clear_search_highlights()


    def _toggle_search_frame(self):
        if self.search_frame_visible:
            self.search_frame.pack_forget()
            self.search_frame_visible = False
            editor = self.get_current_editor()
            if editor:
                if hasattr(editor, 'clear_search_highlights'): # Check if method exists
                    editor.clear_search_highlights()
                editor.text_area.focus_set()
        else:
            # Ensure search_frame is packed correctly, above status_bar
            self.search_frame.pack(side=tk.BOTTOM, fill=tk.X, before=self.status_bar.frame)
            self.search_frame_visible = True
            if hasattr(self, 'search_entry'): # Check if search_entry exists
                 self.search_entry.focus_set()
            self.last_search_match_info = {'index': "1.0", 'query': ""} # Reset search

    def _find_next(self, event=None): # Added event=None for binding
        editor = self.get_current_editor()
        if not editor:
            return
        query = self.search_entry.get()
        if not query:
            editor.clear_search_highlights()
            return

        # If query changed or it's a new search context, reset start index
        if self.last_search_match_info.get('query') != query:
            self.last_search_match_info['index'] = "1.0"

        start_index = self.last_search_match_info.get('index', "1.0")
        editor.clear_search_highlights() # Clear previous before new search

        nocase_flag = not self.case_sensitive_var.get()
        match_start = editor.text_area.search(query, start_index, stopindex=tk.END, nocase=nocase_flag)

        if match_start:
            match_end = f"{match_start}+{len(query)}c" # 'c' for characters
            editor.text_area.tag_add("search_highlight", match_start, match_end)
            editor.text_area.see(match_start)
            editor.text_area.mark_set(tk.INSERT, match_end) # Move cursor to end of match
            self.last_search_match_info = {'index': match_end, 'query': query}
            self.status_bar.update_status(f"Found: '{query}'") # Update status on successful find
        else: # Wrap around search
            self.status_bar.update_status(f"'{query}' not found. Wrapping around.")
            match_start_wrap = editor.text_area.search(query, "1.0", stopindex=start_index, nocase=nocase_flag)
            if match_start_wrap:
                match_end = f"{match_start_wrap}+{len(query)}c"
                editor.text_area.tag_add("search_highlight", match_start_wrap, match_end)
                editor.text_area.see(match_start_wrap)
                editor.text_area.mark_set(tk.INSERT, match_end)
                self.last_search_match_info = {'index': match_end, 'query': query}
                self.status_bar.update_status(f"Wrapped around. Found: '{query}'")
            else:
                self.status_bar.update_status(f"'{query}' not found.")
                self.last_search_match_info = {'index': "1.0", 'query': query} # Reset for next time
        # The 'else' for initial search success was removed in a previous step; status update moved into the 'if match_start' block.

    def _find_previous(self, event=None): # Added event=None for binding
        editor = self.get_current_editor()
        if not editor:
            return
        query = self.search_entry.get()
        if not query:
            editor.clear_search_highlights()
            return

        # If query changed or it's a new search context, reset start index for prev search
        if self.last_search_match_info.get('query') != query:
             # For previous, INSERT is usually where the next search would start forward.
             # So, if query changes, we want to start from current cursor or doc end.
            self.last_search_match_info['index'] = editor.text_area.index(tk.INSERT)

        start_index = self.last_search_match_info.get('index', editor.text_area.index(tk.INSERT))
        editor.clear_search_highlights()

        nocase_flag = not self.case_sensitive_var.get()
        match_start = editor.text_area.search(query, start_index, stopindex="1.0", backwards=True, nocase=nocase_flag)

        if match_start:
            match_end = f"{match_start}+{len(query)}c"
            editor.text_area.tag_add("search_highlight", match_start, match_end)
            editor.text_area.see(match_start)
            editor.text_area.mark_set(tk.INSERT, match_start) # Move cursor to start of match for prev
            self.last_search_match_info = {'index': match_start, 'query': query}
            self.status_bar.update_status(f"Found: '{query}'") # Update status on successful find
        else: # Wrap around search (from end of doc to start_index)
            self.status_bar.update_status(f"'{query}' not found. Wrapping around (previous).")
            match_start_wrap = editor.text_area.search(query, tk.END, stopindex=start_index, backwards=True, nocase=nocase_flag)
            if match_start_wrap:
                match_end = f"{match_start_wrap}+{len(query)}c"
                editor.text_area.tag_add("search_highlight", match_start_wrap, match_end)
                editor.text_area.see(match_start_wrap)
                editor.text_area.mark_set(tk.INSERT, match_start)
                self.last_search_match_info = {'index': match_start, 'query': query}
                self.status_bar.update_status(f"Wrapped around (previous). Found: '{query}'")
            else:
                self.status_bar.update_status(f"'{query}' not found.")
                self.last_search_match_info = {'index': editor.text_area.index(tk.INSERT), 'query': query}
        # The 'else' for initial search success was removed in a previous step; status update moved into the 'if match_start' block.

    def quit_application(self):
        # Iterate over a copy of tab IDs, as closing tabs will modify the notebook
        for tab_id in list(self.notebook.tabs()):
            self.notebook.select(tab_id) # Activate the tab to check it
            editor = self.get_current_editor()
            filepath = self.tab_filepaths.get(tab_id, "Untitled")

            if editor and editor.is_modified:
                response = messagebox.askyesnocancel(
                    "Save changes?",
                    f"Do you want to save changes to {os.path.basename(filepath)}?"
                )
                if response is True: # Yes
                    self.save_file()
                    if editor.is_modified: # Save was cancelled or failed
                        return # Abort quitting
                elif response is None: # Cancel
                    return # Abort quitting
                # If No, continue to next tab or quit

        self.window.destroy() # All clear, or all "No"s

    def close_current_tab(self):
        if not self.notebook.tabs(): # No tabs to close
            return

        current_tab_id = self.notebook.select() # This is the widget ID
        editor_to_close = self.editors.get(current_tab_id)
        filepath_to_close = self.tab_filepaths.get(current_tab_id, "Untitled")

        if editor_to_close and editor_to_close.is_modified:
            response = messagebox.askyesnocancel(
                "Save changes?",
                f"Do you want to save changes to {os.path.basename(filepath_to_close)}?"
            )
            if response is True: # Yes
                self.save_file() # Save the current file
                # Check if save was cancelled (e.g., user closed save dialog)
                # A bit tricky here, save_file doesn't directly return status of dialog.
                # Assuming if still modified, save was cancelled or failed.
                if editor_to_close.is_modified:
                    return # Don't close tab if save was cancelled
            elif response is None: # Cancel
                return # Don't close tab
            # If response is False (No), proceed to close without saving.

        self.notebook.forget(current_tab_id) # Remove tab from notebook view

        # Clean up stored data associated with the closed tab
        if current_tab_id in self.editors:
            del self.editors[current_tab_id]
        if current_tab_id in self.tab_filepaths:
            del self.tab_filepaths[current_tab_id]

        self.update_title_and_status() # Update title/status based on new current tab or if no tabs remain

    def open_file(self):
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("Text Files", "*.txt"), ("Python Files", "*.py"), ("Markdown Files", "*.md"), ("All Files", "*.*")]
            )
            if not filepath:
                return

            with open(filepath, "r") as input_file:
                text_content = input_file.read()

            # self.text_editor.set_content(text_content) # Old way
            self.open_file_in_new_tab(filepath, text_content)
            # self.update_title_and_status(filepath) # update_title_and_status is called by open_file_in_new_tab
        except Exception as e:
            print(f"An error occurred while opening the file: {e}")
            self.status_bar.update_status(f"Error opening file: {os.path.basename(filepath)}")

    def open_file_in_new_tab(self, filepath, content_to_load=None):
        """Opens a file in a new tab, or switches to it if already open."""
        # Check if file is already open by iterating through widget IDs and stored filepaths
        for tab_widget_id in self.notebook.tabs():
            if self.tab_filepaths.get(tab_widget_id) == filepath:
                self.notebook.select(tab_widget_id)
                return

        tab_frame = tk.Frame(self.notebook)
        # Pass App instance to TextEditor
        editor_instance = TextEditor(tab_frame, self.status_bar, self)

        if content_to_load is None:
            try:
                with open(filepath, "r") as input_file:
                    content_to_load = input_file.read()
            except Exception as e:
                print(f"Error reading file for new tab: {e}")
                self.status_bar.update_status(f"Error opening: {os.path.basename(filepath)}")
                # Potentially destroy tab_frame if it was created but not added
                return

        # Pass initial_load=True when first loading content into a new tab
        editor_instance.set_content(content_to_load, initial_load=True)

        self.notebook.add(tab_frame, text=os.path.basename(filepath)) # Initial text without "*"
        # The new tab is automatically selected. Get its ID (widget path).
        current_tab_widget_id = self.notebook.select()

        self.editors[current_tab_widget_id] = editor_instance
        self.tab_filepaths[current_tab_widget_id] = filepath

        self.update_title_and_status() # This will use the newly selected tab

    def get_tab_id_for_editor(self, editor_instance):
        for tab_id, editor in self.editors.items():
            if editor == editor_instance:
                return tab_id
        return None

    def update_tab_text_for_editor(self, editor_instance, is_modified):
        tab_id = self.get_tab_id_for_editor(editor_instance)
        if tab_id:
            base_filename = os.path.basename(self.tab_filepaths.get(tab_id, "Untitled"))
            new_text = base_filename + ("*" if is_modified else "")
            self.notebook.tab(tab_id, text=new_text)

    def get_current_editor(self):
        if not self.notebook.tabs(): # Check if there are any tabs
            return None
        current_tab_id = self.notebook.select() # This is the widget ID (path)
        return self.editors.get(current_tab_id)

    def save_file(self):
        editor = self.get_current_editor()
        if not editor:
            self.status_bar.update_status("No active tab to save.")
            return

        current_tab_id = self.notebook.select() # This is the widget ID
        filepath = self.tab_filepaths.get(current_tab_id)

        if not filepath or filepath == "Untitled": # If it's a new unsaved file or "Untitled"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("Python Files", "*.py"), ("Markdown Files", "*.md"), ("All Files", "*.*")]
            )
            if not filepath: # User cancelled save dialog
                return
            # Update tab text and stored filepath
            self.notebook.tab(current_tab_id, text=os.path.basename(filepath))
            self.tab_filepaths[current_tab_id] = filepath

        try:
            text_content = editor.get_content()
            with open(filepath, "w") as output_file:
                output_file.write(text_content)
            # Mark editor as not modified
            editor.mark_as_modified(False)
            self.update_title_and_status() # Update title/status using current tab info
        except Exception as e:
            print(f"An error occurred while saving the file: {e}")
            self.status_bar.update_status(f"Error saving file: {os.path.basename(filepath)}")

    def on_tab_changed(self, event=None):
        editor = self.get_current_editor()
        if editor:
            # If search frame is visible, clear highlights from newly active tab
            # as they might be from a previous tab's search.
            if self.search_frame_visible: # Check if search frame is active
                 editor.clear_search_highlights()

        self.last_search_match_info = {'index': "1.0", 'query': ""} # Reset search context for new tab

        self.update_title_and_status()

    def update_title_and_status(self):
        if not self.notebook.tabs(): # No tabs open
            self.window.title("Basic Text Editor - Refactored")
            self.status_bar.update_status("Ready. No file open.")
            return

        current_tab_id = self.notebook.select() # This is the widget ID
        current_filepath = self.tab_filepaths.get(current_tab_id, "Untitled")

        # Future: Add more status info from editor if needed
        # editor = self.get_current_editor()

        self.window.title(f"Basic Text Editor - {os.path.basename(current_filepath)}")
        # Update status bar: use the actual filepath if available, otherwise "Untitled"
        self.status_bar.update_filepath(current_filepath if current_filepath != "Untitled" else "Untitled")


    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.quit_application) # Handle window close button
        self.window.mainloop()

    def handle_renamed_file(self, old_path, new_path):
        # Check if the renamed file is open in any tab
        found_tab_id = None
        for tab_id, filepath in self.tab_filepaths.items():
            if filepath == old_path:
                found_tab_id = tab_id
                break

        if found_tab_id:
            editor = self.editors.get(found_tab_id)
            self.tab_filepaths[found_tab_id] = new_path
            new_base_name = os.path.basename(new_path)
            tab_text = new_base_name
            if editor and editor.is_modified:
                tab_text += "*"
            self.notebook.tab(found_tab_id, text=tab_text)

            # If the renamed file is the currently active tab, update the main window title
            if self.notebook.select() == found_tab_id:
                self.update_title_and_status()

    def handle_deleted_file(self, deleted_path):
        # Check if the deleted file is open in any tab
        found_tab_id = None
        for tab_id, filepath in self.tab_filepaths.items():
            if filepath == deleted_path:
                found_tab_id = tab_id
                break

        if found_tab_id:
            # Force close the tab without saving, as the file is gone
            self.notebook.forget(found_tab_id)
            if found_tab_id in self.editors:
                # Potentially clean up editor resources if any were held (TextEditor currently doesn't have explicit cleanup)
                del self.editors[found_tab_id]
            if found_tab_id in self.tab_filepaths:
                del self.tab_filepaths[found_tab_id]

            self.update_title_and_status() # Update title as the current tab might have changed or closed
