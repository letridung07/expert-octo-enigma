# Import the Tkinter library
import tkinter as tk
from tkinter import Text, filedialog, Menu, ttk, messagebox, simpledialog
import os
import re
import shutil

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

class FileExplorer:
    def __init__(self, master_frame, text_editor_instance, app_instance):
        self.frame = master_frame
        self.text_editor = text_editor_instance # Note: This is actually app_instance for callbacks now
        self.app = app_instance

        self._load_icons() # Load icons first

        self.file_tree = ttk.Treeview(self.frame)
        self.file_tree.pack(expand=True, fill='both')
        self.file_tree["columns"] = ("path", "type") # Added type for storing 'file'/'directory'
        self.file_tree.heading("#0", text="Name", anchor="w")
        self.file_tree.column("#0", anchor="w", width=180) # Adjusted width
        self.file_tree.column("path", width=0, stretch=tk.NO)
        self.file_tree.column("type", width=0, stretch=tk.NO) # Hidden type column
        self.current_path = os.getcwd()

        self._create_context_menu()
        # Initial population of the root level
        self.populate_file_explorer("", self.current_path)
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_select)
        self.file_tree.bind("<<TreeviewOpen>>", self._on_treeview_open) # For expanding directories
        self.file_tree.bind("<Button-3>", self._show_context_menu) # For Windows/Linux

    def _create_context_menu(self):
        self.context_menu = Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="New File", command=self._create_new_file)
        self.context_menu.add_command(label="New Folder", command=self._create_new_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rename", command=self._rename_item)
        self.context_menu.add_command(label="Delete", command=self._delete_item)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Refresh", command=self._refresh_explorer)

    def _show_context_menu(self, event):
        item_id = self.file_tree.identify_row(event.y)
        if item_id:
            self.file_tree.selection_set(item_id) # Select the item under cursor
            # Enable/disable menu items based on selection (e.g. if it's a file or folder)
            # For now, all are enabled if an item is selected
            self.context_menu.entryconfig("New File", state="normal")
            self.context_menu.entryconfig("New Folder", state="normal")
            self.context_menu.entryconfig("Rename", state="normal")
            self.context_menu.entryconfig("Delete", state="normal")
        else:
            # Clicked on empty area - only allow New File/Folder in current_path
            self.file_tree.selection_set('') # Clear selection
            self.context_menu.entryconfig("New File", state="normal")
            self.context_menu.entryconfig("New Folder", state="normal")
            self.context_menu.entryconfig("Rename", state="disabled")
            self.context_menu.entryconfig("Delete", state="disabled")
        self.context_menu.entryconfig("Refresh", state="normal") # Refresh is always enabled

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _refresh_explorer(self):
        # Clear all root items. TreeviewOpen handler will populate subdirectories upon expansion.
        for item_id in self.file_tree.get_children(""): # Get children of root
            self.file_tree.delete(item_id)
        # Repopulate from the current_path at the root level
        self.populate_file_explorer("", self.current_path)


    def populate_file_explorer(self, parent_node_id, dir_path):
        """Populates the treeview with items from dir_path under parent_node_id."""
        try:
            for item_name in sorted(os.listdir(dir_path)):
                full_path = os.path.join(dir_path, item_name)
                item_type = "directory" if os.path.isdir(full_path) else "file"

                # Determine icon
                icon_to_use = None
                if item_type == "directory" and self.folder_icon:
                    icon_to_use = self.folder_icon
                elif item_type == "file" and self.file_icon:
                    icon_to_use = self.file_icon

                item_id = self.file_tree.insert(parent_node_id, 'end', text=item_name,
                                                image=icon_to_use if icon_to_use else "", # Use icon if available
                                                values=[full_path, item_type], open=False)

                # If it's a directory, insert a placeholder to make it expandable
                if item_type == "directory":
                    # Check if directory is empty or not readable before adding placeholder
                    try:
                        if os.listdir(full_path): # If not empty
                             self.file_tree.insert(item_id, 'end', text='...', values=['placeholder', 'placeholder'])
                        # If empty, it will just be an expandable node with no children shown yet
                    except OSError: # Permission error etc.
                        self.file_tree.insert(item_id, 'end', text='[Error reading]', values=['error', 'error'])
        except OSError as e:
            # Error listing the initial dir_path (e.g. permission denied for dir_path itself)
            # If parent_node_id is "", it's the root, display error there.
            # Otherwise, could try to insert an error node under the parent.
            error_node_parent = parent_node_id if parent_node_id else ""
            self.file_tree.insert(error_node_parent, 'end', text=f"[Error: {os.path.basename(dir_path)}]",
                                  values=[dir_path, "error"])
            print(f"Error populating file explorer for {dir_path}: {e}")


    def _on_treeview_open(self, event):
        selected_node_id = self.file_tree.focus() # Get the node that is being opened
        if not selected_node_id: return

        children = self.file_tree.get_children(selected_node_id)
        # If the first child is a placeholder, expand this directory
        if children and self.file_tree.item(children[0])['values'][0] == 'placeholder':
            self.file_tree.delete(children[0]) # Remove placeholder

            dir_path_to_expand = self.file_tree.item(selected_node_id)['values'][0]
            if os.path.isdir(dir_path_to_expand):
                self.populate_file_explorer(selected_node_id, dir_path_to_expand)
            else: # Should not happen if placeholder logic is correct
                print(f"Error: Attempted to expand a non-directory: {dir_path_to_expand}")


    def _load_icons(self):
        # Using a minimal transparent GIF as placeholder if actual icons are not available
        # R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7 (1x1 transparent GIF)
        b64_transparent_pixel = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        # Ensure PhotoImage is associated with the correct Tkinter root/toplevel
        # This is important in test environments or complex Tkinter setups.
        master_for_images = self.frame.winfo_toplevel()
        try:
            self.folder_icon = tk.PhotoImage(name="folder_icon_data", data=b64_transparent_pixel, master=master_for_images)
            self.file_icon = tk.PhotoImage(name="file_icon_data", data=b64_transparent_pixel, master=master_for_images)
            # In a real scenario, replace b64_transparent_pixel with actual base64 encoded icon data
            # e.g., self.folder_icon = tk.PhotoImage(file="icons/folder.png")
        except tk.TclError: # Fallback if PhotoImage fails
            self.folder_icon = None
            self.file_icon = None
            print("Warning: Could not load icons for File Explorer. Tkinter TclError.")
        except Exception as e: # Catch any other error during icon loading
            self.folder_icon = None
            self.file_icon = None
            print(f"Warning: An unexpected error occurred while loading icons: {e}")


    def _get_parent_dir_for_new_item(self):
        selected_items = self.file_tree.selection() # Use selection() as it returns a tuple
        if selected_items: # Check if the tuple is not empty
            selected_item_id = selected_items[0]
            # Ensure 'values' exist and has at least two items before accessing values[1]
            item_details = self.file_tree.item(selected_item_id)
            if item_details and 'values' in item_details and len(item_details['values']) > 1:
                item_path = item_details['values'][0]
                item_type = item_details['values'][1] # 'directory' or 'file'
                if item_type == "directory":
                    return item_path
                else: # A file is selected, use its directory
                    return os.path.dirname(item_path)
        return self.current_path # Default to current root

    def _create_new_folder(self):
        parent_dir = self._get_parent_dir_for_new_item()
        foldername = simpledialog.askstring("New Folder", "Enter folder name:", parent=self.frame)
        if foldername:
            try:
                full_path = os.path.join(parent_dir, foldername)
                os.mkdir(full_path)
                self.populate_file_explorer(self.current_path) # Refresh
                if self.app: self.app.status_bar.update_status(f"Folder '{foldername}' created in {parent_dir}.")
            except FileExistsError:
                messagebox.showerror("Error", f"Folder '{foldername}' already exists in {parent_dir}.", parent=self.frame)
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create folder: {e}", parent=self.frame)

    def _create_new_file(self):
        parent_dir = self._get_parent_dir_for_new_item()
        filename = simpledialog.askstring("New File", "Enter file name:", parent=self.frame)
        if filename:
            try:
                full_path = os.path.join(parent_dir, filename)
                if os.path.exists(full_path):
                     messagebox.showerror("Error", f"File '{filename}' already exists in {parent_dir}.", parent=self.frame)
                     return
                open(full_path, 'w').close() # Create empty file
                self.populate_file_explorer(self.current_path) # Refresh
                if self.app: self.app.status_bar.update_status(f"File '{filename}' created in {parent_dir}.")
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create file: {e}", parent=self.frame)

    def _rename_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showwarning("Rename", "No item selected to rename.", parent=self.frame)
            return

        selected_item_id = selected_items[0] # Assuming single selection for rename
        old_path = self.file_tree.item(selected_item_id)['values'][0]
        old_name = os.path.basename(old_path)

        new_name = simpledialog.askstring("Rename", f"Enter new name for '{old_name}':",
                                          initialvalue=old_name, parent=self.frame)

        if new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                self.populate_file_explorer(self.current_path) # Refresh explorer
                # Notify App to update any open tabs
                if self.app:
                    self.app.handle_renamed_file(old_path, new_path)
                    self.app.status_bar.update_status(f"Renamed '{old_name}' to '{new_name}'.")
            except OSError as e:
                messagebox.showerror("Error", f"Failed to rename item: {e}", parent=self.frame)

    def _delete_item(self):
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showwarning("Delete", "No item selected to delete.", parent=self.frame)
            return

        selected_item_id = selected_items[0]
        path_to_delete = self.file_tree.item(selected_item_id)['values'][0]
        item_name = os.path.basename(path_to_delete)

        confirm = messagebox.askyesno("Delete", f"Are you sure you want to delete '{item_name}'?", parent=self.frame)
        if confirm:
            try:
                if os.path.isfile(path_to_delete):
                    os.remove(path_to_delete)
                elif os.path.isdir(path_to_delete):
                    shutil.rmtree(path_to_delete)

                self.populate_file_explorer(self.current_path) # Refresh explorer
                # Notify App to close any open tab for this file
                if self.app:
                    self.app.handle_deleted_file(path_to_delete)
                    self.app.status_bar.update_status(f"Deleted '{item_name}'.")
            except OSError as e:
                messagebox.showerror("Error", f"Failed to delete item: {e}", parent=self.frame)

    def _on_file_select(self, event=None):
        selected_items_tuple = self.file_tree.selection()
        if selected_items_tuple:
            selected_item_id = selected_items_tuple[0] # Get the actual item ID string
            # Request the 'values' for this specific item ID
            item_values_tuple = self.file_tree.item(selected_item_id, "values")
            # Ensure item_values_tuple is a non-empty sequence before trying to access its elements
            if item_values_tuple and len(item_values_tuple) > 0:
                filepath = item_values_tuple[0] # filepath is the first value
                if os.path.isfile(filepath):
                    # self.text_editor.set_content is no longer valid here.
                    # The App class (self.app) handles opening the file in a new tab.
                    self.app.open_file_in_new_tab(filepath)
                    # Title and status will be updated by open_file_in_new_tab via on_tab_changed
                # else:
                    # Optionally handle directory selection, e.g., expand it in Treeview
                    # print(f"Directory selected: {filepath}")


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


if __name__ == "__main__":
    app = App()
    app.run()
