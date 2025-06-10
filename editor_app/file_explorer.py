import tkinter as tk
from tkinter import ttk, Menu, simpledialog, messagebox
import os
import shutil

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
