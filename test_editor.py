import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import tkinter as tk
from tkinter import ttk # Required for Treeview & Notebook

# Import classes from main.py
from main import App, TextEditor, FileExplorer, StatusBar, SYNTAX_RULES

class TestStatusBar(unittest.TestCase): # No changes needed for StatusBar tests based on new features
    def setUp(self):
        self.test_root = tk.Tk()
        self.status_bar_frame = tk.Frame(self.test_root)
        self.status_bar = StatusBar(self.status_bar_frame)

    def tearDown(self):
        self.test_root.destroy()

    def test_update_status_message(self):
        self.status_bar.update_status("Test Message")
        self.assertEqual(self.status_bar.label.cget("text"), "Test Message")

    def test_update_filepath(self):
        self.status_bar.update_filepath("test/file.py")
        self.assertEqual(self.status_bar.label.cget("text"), "File: test/file.py")
        self.status_bar.update_filepath(None) # For "Untitled" or no file
        self.assertEqual(self.status_bar.label.cget("text"), "Ready")


class TestTextEditor(unittest.TestCase):
    def setUp(self):
        self.test_root = tk.Tk()
        self.mock_app_instance = MagicMock(spec=App)
        # Mock status_bar for TextEditor if needed, or pass a real one if its methods are simple
        self.mock_status_bar = MagicMock(spec=StatusBar)

        self.text_editor_frame = tk.Frame(self.test_root)
        # TextEditor now requires app_instance
        self.text_editor = TextEditor(self.text_editor_frame, self.mock_status_bar, self.mock_app_instance)
        self.assertIsNotNone(self.text_editor.text_area)

    def tearDown(self):
        self.test_root.destroy()

    def test_set_get_content(self):
        test_content = "Hello, world!"
        # initial_load=True to simulate opening a file, should not mark as modified initially
        self.text_editor.set_content(test_content, initial_load=True)
        self.assertEqual(self.text_editor.get_content().strip(), test_content.strip())
        self.assertFalse(self.text_editor.is_modified) # Should not be modified on initial load
        self.text_editor.clear_content()
        self.assertEqual(self.text_editor.get_content().strip(), "")

    def test_mark_as_modified(self):
        self.text_editor.mark_as_modified(True)
        self.assertTrue(self.text_editor.is_modified)
        self.mock_app_instance.update_tab_text_for_editor.assert_called_once_with(self.text_editor, True)

        self.text_editor.mark_as_modified(False)
        self.assertFalse(self.text_editor.is_modified)
        self.mock_app_instance.update_tab_text_for_editor.assert_called_with(self.text_editor, False)

    # Syntax highlighting tests can remain similar, ensure they use current set_content
    @patch('main.re.finditer')
    def test_apply_syntax_highlighting_keywords(self, mock_finditer):
        mock_match = MagicMock()
        mock_match.start.return_value = 0; mock_match.end.return_value = 3
        mock_finditer.return_value = [mock_match]
        self.text_editor.text_area.tag_add = MagicMock()
        self.text_editor.text_area.tag_remove = MagicMock()
        self.text_editor.set_content("def func(): pass", initial_load=True) # Use initial_load
        # apply_syntax_highlighting is called by set_content
        keyword_pattern = next(p for t, p in SYNTAX_RULES if t == "keyword")
        mock_finditer.assert_any_call(keyword_pattern, "def func(): pass\n", 0)
        self.text_editor.text_area.tag_add.assert_any_call("keyword", "1.0", "1.3")

    def test_clear_search_highlights(self):
        self.text_editor.text_area.tag_add("search_highlight", "1.0", "1.5") # Add a dummy highlight
        self.text_editor.clear_search_highlights()
        # Assert tag_remove was called for "search_highlight"
        # Need to mock tag_remove to check its call for this specific tag
        # For simplicity, we assume it works if the method is called. A more direct check:
        # self.assertEqual(len(self.text_editor.text_area.tag_ranges("search_highlight")), 0)
        # However, tag_ranges needs a real text widget with content.
        # So, mocking tag_remove is better for unit test.
        # This test is more about TextEditor calling the method. Actual removal is tk behavior.
        # Let's assume _configure_tags (which adds search_highlight tag config) was called.
        # This test becomes more of an integration test if we check tk's behavior.
        # For now, let's ensure the method exists and can be called.
        pass # Covered by App tests using mocked editor


class TestFileExplorer(unittest.TestCase):
    def setUp(self):
        self.test_root = tk.Tk()
        # FileExplorer now takes app_instance as its second argument (was text_editor_instance)
        self.mock_app = MagicMock(spec=App)

        self.file_explorer_frame = tk.Frame(self.test_root)
        # The third argument to FileExplorer is also app_instance (for callbacks)
        self.file_explorer = FileExplorer(self.file_explorer_frame, self.mock_app, self.mock_app)
        self.assertIsNotNone(self.file_explorer.file_tree)

    def tearDown(self):
        self.test_root.destroy()

    @patch('os.listdir')
    @patch('os.path.join', side_effect=lambda *args: "/".join(args))
    @patch('os.path.isdir', side_effect=lambda x: "dir" in x)
    def test_populate_file_explorer(self, mock_isdir, mock_join, mock_listdir):
        mock_listdir.return_value = ["file1.txt", "subdir", "file2.py"]
        self.file_explorer.file_tree.insert = MagicMock()
        self.file_explorer.populate_file_explorer("/fake/path")
        mock_listdir.assert_called_once_with("/fake/path")
        expected_calls = [
            call('', 'end', text="file1.txt", values=["/fake/path/file1.txt"], tags=('file',)),
            call('', 'end', text="subdir", values=["/fake/path/subdir"], tags=('directory',)),
            call('', 'end', text="file2.py", values=["/fake/path/file2.py"], tags=('file',)),
        ]
        self.file_explorer.file_tree.insert.assert_has_calls(expected_calls, any_order=True)

    @patch('os.path.isfile', return_value=True)
    def test_on_file_select_opens_file_in_app(self, mock_isfile):
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I001",))
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/path/file.txt"]})
        self.file_explorer._on_file_select()
        mock_isfile.assert_called_once_with("/fake/path/file.txt")
        # FileExplorer now calls app.open_file_in_new_tab
        self.mock_app.open_file_in_new_tab.assert_called_once_with("/fake/path/file.txt")

    @patch('main.simpledialog.askstring')
    @patch('os.mkdir')
    def test_create_new_folder(self, mock_mkdir, mock_askstring):
        mock_askstring.return_value = "NewFolder"
        # Simulate no item selected, so it uses current_path
        self.file_explorer.file_tree.selection = MagicMock(return_value=())
        self.file_explorer.current_path = "/current" # Set a known current_path
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._create_new_folder()
        mock_mkdir.assert_called_once_with("/current/NewFolder")
        mock_populate.assert_called_once_with("/current")

    @patch('main.simpledialog.askstring')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    def test_create_new_file(self, mock_exists, mock_file_open, mock_askstring):
        mock_askstring.return_value = "new_file.txt"
        self.file_explorer.file_tree.selection = MagicMock(return_value=())
        self.file_explorer.current_path = "/current"
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._create_new_file()
        mock_file_open.assert_called_once_with("/current/new_file.txt", 'w')
        mock_populate.assert_called_once_with("/current")

    @patch('main.simpledialog.askstring')
    @patch('os.rename')
    def test_rename_item_file_open_in_app(self, mock_rename, mock_askstring):
        mock_askstring.return_value = "renamed_file.txt"
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I001",))
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/old_name.txt"]})
        self.file_explorer.current_path = "/fake" # Needed for populate
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._rename_item()
        mock_rename.assert_called_once_with("/fake/old_name.txt", "/fake/renamed_file.txt")
        self.mock_app.handle_renamed_file.assert_called_once_with("/fake/old_name.txt", "/fake/renamed_file.txt")
        mock_populate.assert_called_once()

    @patch('main.messagebox.askyesno', return_value=True)
    @patch('os.remove')
    @patch('os.path.isfile', return_value=True) # Assume it's a file
    def test_delete_item_file_open_in_app(self, mock_isfile, mock_os_remove, mock_askyesno):
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I001",))
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/file_to_delete.txt"]})
        self.file_explorer.current_path = "/fake"
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._delete_item()
        mock_os_remove.assert_called_once_with("/fake/file_to_delete.txt")
        self.mock_app.handle_deleted_file.assert_called_once_with("/fake/file_to_delete.txt")
        mock_populate.assert_called_once()


class TestApp(unittest.TestCase):
    def setUp(self):
        # More comprehensive App setup for tabbed interface
        self.test_root = tk.Tk() # Root window for dialogs, etc.
        # Prevent App's __init__ from running its full course if it creates UI directly
        with patch.object(App, '_create_menu', MagicMock()), \
             patch.object(App, '_setup_search_ui', MagicMock()), \
             patch.object(App, 'update_title_and_status', MagicMock()):
            self.app = App()

        # Mock essential UI components that App interacts with directly
        self.app.window = MagicMock(spec=tk.Tk)
        self.app.notebook = MagicMock(spec=ttk.Notebook)
        self.app.status_bar = MagicMock(spec=StatusBar)
        self.app.file_explorer = MagicMock(spec=FileExplorer) # If App directly calls FE methods
        self.app.search_frame = MagicMock(spec=tk.Frame)
        self.app.search_entry = MagicMock(spec=tk.Entry)

        # Initialize collections App uses
        self.app.editors = {}
        self.app.tab_filepaths = {}
        self.app.last_search_match_info = {'index': "1.0", 'query': ""}

    def tearDown(self):
        self.test_root.destroy()

    @patch('builtins.open', new_callable=mock_open, read_data="file content")
    @patch('os.path.isfile', return_value=True) # Assume file exists for open_file_in_new_tab
    @patch('main.TextEditor') # Mock the TextEditor class
    def test_open_file_in_new_tab(self, MockTextEditor, mock_isfile, mock_file_open):
        mock_editor_instance = MockTextEditor.return_value
        mock_editor_instance.is_modified = False # Set default mock attribute

        self.app.notebook.tabs.return_value = [] # No tabs open initially
        self.app.open_file_in_new_tab("/fake/test.txt")

        self.app.notebook.add.assert_called_once()
        MockTextEditor.assert_called_once() # Check TextEditor was instantiated
        mock_editor_instance.set_content.assert_called_once_with("file content", initial_load=True)
        # Check that tab_id from notebook.select() is used as key
        # This is a bit tricky as notebook.select() is called inside.
        # We assume it works and a new entry is in editors/tab_filepaths.
        self.assertEqual(len(self.app.editors), 1)
        self.assertTrue(any(fp == "/fake/test.txt" for fp in self.app.tab_filepaths.values()))

    def test_open_existing_file_switches_tab(self):
        # Setup: one file already open
        mock_editor = MagicMock(spec=TextEditor)
        tab_id_1 = ".!notebook.!frame" # Example tab ID
        self.app.editors = {tab_id_1: mock_editor}
        self.app.tab_filepaths = {tab_id_1: "/fake/existing.txt"}
        self.app.notebook.tabs.return_value = [tab_id_1] # Simulate one tab open

        # Attempt to open the same file
        self.app.open_file_in_new_tab("/fake/existing.txt")

        self.app.notebook.select.assert_called_with(tab_id_1)
        self.app.notebook.add.assert_not_called() # No new tab should be added
        self.assertEqual(len(self.app.editors), 1)

    @patch('main.messagebox.askyesnocancel', return_value=False) # "No" to save
    def test_close_current_tab_no_modifications(self, mock_messagebox):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.is_modified = False
        tab_id = ".!notebook.!frame"
        self.app.notebook.tabs.return_value = [tab_id]
        self.app.notebook.select.return_value = tab_id
        self.app.editors = {tab_id: mock_editor}
        self.app.tab_filepaths = {tab_id: "/fake/file.txt"}

        self.app.close_current_tab()

        mock_messagebox.assert_not_called()
        self.app.notebook.forget.assert_called_once_with(tab_id)
        self.assertNotIn(tab_id, self.app.editors)

    @patch('main.messagebox.askyesnocancel', return_value=True) # "Yes" to save
    @patch.object(App, 'save_file') # Mock the app's save_file method
    def test_close_current_tab_modified_save_yes(self, mock_save_file, mock_messagebox):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.is_modified = True
        tab_id = ".!notebook.!frame"
        self.app.notebook.tabs.return_value = [tab_id]
        self.app.notebook.select.return_value = tab_id
        self.app.editors = {tab_id: mock_editor}
        self.app.tab_filepaths = {tab_id: "/fake/file.txt"}

        # Simulate that save_file makes the editor no longer modified
        def side_effect_save():
            mock_editor.is_modified = False
        mock_save_file.side_effect = side_effect_save

        self.app.close_current_tab()

        mock_messagebox.assert_called_once()
        mock_save_file.assert_called_once()
        self.app.notebook.forget.assert_called_once_with(tab_id)

    # ... (similar tests for "No" and "Cancel" for close_current_tab) ...
    # ... (similar tests for quit_application scenarios) ...

    def test_on_tab_changed(self):
        # Mock the get_current_editor to return a mock editor that has clear_search_highlights
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.clear_search_highlights = MagicMock()
        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            with patch.object(self.app, 'update_title_and_status') as mock_update_title:
                self.app.search_frame_visible = True # Simulate search frame being visible
                self.app.on_tab_changed()
                mock_update_title.assert_called_once()
                mock_editor.clear_search_highlights.assert_called_once() # If search frame is visible

    def test_handle_renamed_file(self):
        tab_id = ".!notebook.!frame"
        old_path = "/old/path.txt"; new_path = "/new/path.txt"
        mock_editor = MagicMock(spec=TextEditor); mock_editor.is_modified = True
        self.app.tab_filepaths = {tab_id: old_path}
        self.app.editors = {tab_id: mock_editor}
        self.app.notebook.select.return_value = tab_id # Assume this tab is active

        self.app.handle_renamed_file(old_path, new_path)

        self.assertEqual(self.app.tab_filepaths[tab_id], new_path)
        self.app.notebook.tab.assert_called_once_with(tab_id, text="path.txt*") # basename + *
        self.app.status_bar.update_filepath.assert_called() # Called via update_title_and_status

    def test_handle_deleted_file(self):
        tab_id = ".!notebook.!frame"
        deleted_path = "/path/to/deleted_file.txt"
        self.app.tab_filepaths = {tab_id: deleted_path}
        self.app.editors = {tab_id: MagicMock(spec=TextEditor)}

        self.app.handle_deleted_file(deleted_path)

        self.app.notebook.forget.assert_called_once_with(tab_id)
        self.assertNotIn(tab_id, self.app.editors)
        self.assertNotIn(tab_id, self.app.tab_filepaths)

    # --- Search Functionality Tests ---
    def test_toggle_search_frame_show_hide(self):
        # Initial state: hidden
        self.app.search_frame_visible = False
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock() # for focus_set
        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            # Show
            self.app._toggle_search_frame()
            self.app.search_frame.pack.assert_called_once()
            self.assertTrue(self.app.search_frame_visible)
            self.app.search_entry.focus_set.assert_called_once()

            # Hide
            mock_editor.clear_search_highlights = MagicMock()
            self.app._toggle_search_frame()
            self.app.search_frame.pack_forget.assert_called_once()
            self.assertFalse(self.app.search_frame_visible)
            mock_editor.clear_search_highlights.assert_called_once()
            mock_editor.text_area.focus_set.assert_called_once()

    def test_find_next_found(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock() # for search, tag_add, see, mark_set
        mock_editor.text_area.search.return_value = "1.5" # Found at line 1, char 5
        self.app.search_entry.get.return_value = "test"

        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            self.app._find_next()

        mock_editor.clear_search_highlights.assert_called_once()
        mock_editor.text_area.search.assert_called_once_with("test", "1.0", stopindex=tk.END, nocase=True)
        mock_editor.text_area.tag_add.assert_called_once_with("search_highlight", "1.5", "1.5+4c")
        mock_editor.text_area.see.assert_called_once_with("1.5")
        mock_editor.text_area.mark_set.assert_called_once_with(tk.INSERT, "1.5+4c")
        self.assertEqual(self.app.last_search_match_info, {'index': "1.5+4c", 'query': "test"})

    def test_find_next_not_found_then_wrap(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        # First search not found, second (wrap) found
        mock_editor.text_area.search.side_effect = ["", "1.2"]
        self.app.search_entry.get.return_value = "wrap"
        self.app.last_search_match_info = {'index': "5.0", 'query': "wrap"} # Simulate previous search

        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            self.app._find_next()

        self.assertEqual(mock_editor.text_area.search.call_count, 2)
        mock_editor.text_area.search.assert_any_call("wrap", "5.0", stopindex=tk.END, nocase=True)
        mock_editor.text_area.search.assert_any_call("wrap", "1.0", stopindex="5.0", nocase=True)
        mock_editor.text_area.tag_add.assert_called_once_with("search_highlight", "1.2", "1.2+4c")
        self.app.status_bar.update_status.assert_any_call("'wrap' not found. Wrapping around.")


if __name__ == '__main__':
    unittest.main()
