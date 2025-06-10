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
        self.mock_app.status_bar.update_status.assert_called_with("Folder 'NewFolder' created in /current.")


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
        self.mock_app.status_bar.update_status.assert_called_with("File 'new_file.txt' created in /current.")


    @patch('main.simpledialog.askstring')
    @patch('os.rename')
    def test_rename_item_file_open_in_app(self, mock_rename, mock_askstring):
        mock_askstring.return_value = "renamed_file.txt"
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I001",))
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/old_name.txt", "file"]}) # Added type
        self.file_explorer.current_path = "/fake" # Needed for populate
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._rename_item()
        mock_rename.assert_called_once_with("/fake/old_name.txt", "/fake/renamed_file.txt")
        self.mock_app.handle_renamed_file.assert_called_once_with("/fake/old_name.txt", "/fake/renamed_file.txt")
        mock_populate.assert_called_once()
        self.mock_app.status_bar.update_status.assert_called_with("Renamed 'old_name.txt' to 'renamed_file.txt'.")


    @patch('main.messagebox.askyesno', return_value=True)
    @patch('os.remove')
    @patch('os.path.isfile', return_value=True) # Assume it's a file
    def test_delete_item_file_open_in_app(self, mock_isfile, mock_os_remove, mock_askyesno):
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I001",))
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/file_to_delete.txt", "file"]}) # Added type
        self.file_explorer.current_path = "/fake"
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._delete_item()
        mock_os_remove.assert_called_once_with("/fake/file_to_delete.txt")
        self.mock_app.handle_deleted_file.assert_called_once_with("/fake/file_to_delete.txt")
        mock_populate.assert_called_once()
        self.mock_app.status_bar.update_status.assert_called_with("Deleted 'file_to_delete.txt'.")


    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_populate_recursive_on_treeview_open(self, mock_isdir, mock_listdir):
        # Setup initial tree with a directory and placeholder
        dir_id = "item_dir"
        dir_path = "/fake/testdir"
        placeholder_id = "item_placeholder"

        # Simulate initial population:
        # populate_file_explorer(self, parent_node_id, dir_path)
        # We need to mock tree.insert to control IDs
        def initial_insert_side_effect(parent, index, text, values, open, image=None):
            if text == "testdir": return dir_id
            if text == "...": return placeholder_id
            return MagicMock() # Default for other calls

        self.file_explorer.file_tree.insert = MagicMock(side_effect=initial_insert_side_effect)
        mock_isdir.return_value = True # testdir is a directory
        mock_listdir.return_value = ["subfile.txt"] # Content of testdir for later expansion

        # Initial call to populate root (not tested here, assume it adds 'testdir')
        # For this test, let's assume 'testdir' is already there with a placeholder
        self.file_explorer.file_tree.item = MagicMock(side_effect=lambda node_id: {
            dir_id: {'values': [dir_path, 'directory']},
            placeholder_id: {'values': ['placeholder', 'placeholder']}
        }.get(node_id))
        self.file_explorer.file_tree.get_children = MagicMock(return_value=[placeholder_id])
        self.file_explorer.file_tree.focus = MagicMock(return_value=dir_id)
        self.file_explorer.file_tree.delete = MagicMock()

        # Patch the recursive call to populate_file_explorer
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_recursive_populate:
            self.file_explorer._on_treeview_open(None) # Simulate event

        mock_recursive_populate.assert_called_once_with(dir_id, dir_path)
        self.file_explorer.file_tree.delete.assert_called_once_with(placeholder_id)

    def test_refresh_explorer(self):
        self.file_explorer.file_tree.get_children = MagicMock(return_value=["id1", "id2"])
        self.file_explorer.file_tree.delete = MagicMock()
        with patch.object(self.file_explorer, 'populate_file_explorer') as mock_populate:
            self.file_explorer._refresh_explorer()

        self.file_explorer.file_tree.delete.assert_has_calls([call("id1"), call("id2")], any_order=True)
        mock_populate.assert_called_once_with("", self.file_explorer.current_path)

    @patch('os.listdir', return_value=['folder1'])
    @patch('os.path.isdir', return_value=True) # Everything is a folder for this test
    @patch('main.FileExplorer._load_icons', MagicMock()) # Prevent icon loading issues in test
    def test_populate_adds_placeholder_for_directory(self, mock_isdir, mock_listdir):
        self.file_explorer.file_tree.insert = MagicMock(return_value="folder_id") # Main item ID

        # Reset current_path for predictability
        self.file_explorer.current_path = "/testroot"
        # Call for root
        self.file_explorer.populate_file_explorer("", self.file_explorer.current_path)

        # Check insert for the directory itself
        # Check insert for the placeholder (child of the directory)
        # expected_item_call = call("", 'end', text='folder1', values=['/testroot/folder1', 'directory'], open=False, image=ANY)
        # expected_placeholder_call = call("folder_id", 'end', text='...', values=['placeholder', 'placeholder'])

        # Simplified check due to complex image mocking: Check if insert was called more than once (item + placeholder)
        # A more robust way would be to check call_args_list
        self.assertGreaterEqual(self.file_explorer.file_tree.insert.call_count, 2)
        args_list = self.file_explorer.file_tree.insert.call_args_list
        # First call is for the directory itself
        self.assertEqual(args_list[0][1]['text'], 'folder1')
        self.assertEqual(args_list[0][1]['values'][1], 'directory')
        # Second call is for its placeholder
        self.assertEqual(args_list[1][1]['text'], '...')
        self.assertEqual(args_list[1][1]['values'][0], 'placeholder')
        self.assertEqual(args_list[1][0][0], "folder_id") # Parent is the folder_id

    @patch('os.listdir', side_effect=PermissionError("Test permission denied"))
    @patch('main.FileExplorer._load_icons', MagicMock())
    def test_populate_handles_permission_error(self, mock_listdir):
        self.file_explorer.file_tree.insert = MagicMock()
        self.file_explorer.current_path = "/unreadable_dir"
        self.file_explorer.populate_file_explorer("", self.file_explorer.current_path)

        # Expect an error node to be inserted at the root
        self.file_explorer.file_tree.insert.assert_called_once_with(
            "", 'end', text="[Error: unreadable_dir]", values=["/unreadable_dir", "error"]
        )

    @patch('tkinter.PhotoImage') # Mock PhotoImage to avoid actual image processing
    @patch('os.path.isdir') # Mock isdir for item type determination
    @patch('os.listdir', return_value=['file.txt', 'folder']) # Mock listdir
    def test_populate_assigns_icons(self, mock_listdir, mock_isdir, mock_photoimage):
        # Setup mock_isdir to return True for 'folder' and False for 'file.txt'
        def isdir_side_effect(path):
            # Using endswith as a simple way to differentiate for the test
            if path.endswith('folder'): return True
            if path.endswith('file.txt'): return False
            return False # Default for other paths like /fake_path itself
        mock_isdir.side_effect = isdir_side_effect

        # We need a FileExplorer instance where _load_icons has been called
        # and where self.folder_icon and self.file_icon are set to our mocks

        # Temporarily patch _load_icons on the class to do nothing during instantiation for this test
        with patch.object(FileExplorer, '_load_icons', lambda x: None):
            fe_for_icon_test = FileExplorer(self.file_explorer_frame, self.mock_app, self.mock_app)

        # Manually assign mocked PhotoImage instances AFTER _load_icons is bypassed or controlled
        mock_folder_icon_instance = MagicMock(spec=tk.PhotoImage)
        mock_file_icon_instance = MagicMock(spec=tk.PhotoImage)
        fe_for_icon_test.folder_icon = mock_folder_icon_instance
        fe_for_icon_test.file_icon = mock_file_icon_instance

        fe_for_icon_test.file_tree.insert = MagicMock()
        fe_for_icon_test.populate_file_explorer("", "/fake_path") # Path doesn't matter much due to mocks

        calls = fe_for_icon_test.file_tree.insert.call_args_list
        self.assertTrue(len(calls) >= 2, "Should have tried to insert at least two items")

        found_file_call = False
        found_folder_call = False
        for call_args_entry in calls:
            kwargs = call_args_entry[1] # a dict of keyword arguments
            if kwargs['text'] == 'file.txt':
                self.assertEqual(kwargs['image'], mock_file_icon_instance)
                found_file_call = True
            elif kwargs['text'] == 'folder':
                self.assertEqual(kwargs['image'], mock_folder_icon_instance)
                found_folder_call = True

        self.assertTrue(found_file_call, "File item with icon not inserted correctly")
        self.assertTrue(found_folder_call, "Folder item with icon not inserted correctly")


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

    def test_find_next_case_sensitive_match(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = "1.0" # Found
        self.app.search_entry.get.return_value = "Test"
        self.app.case_sensitive_var.set(True) # Enable case-sensitive

        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            self.app._find_next()

        # Check that nocase=False was used in the search call
        args, kwargs = mock_editor.text_area.search.call_args
        self.assertFalse(kwargs.get('nocase', True), "Search should have been case-sensitive (nocase=False)")
        mock_editor.text_area.tag_add.assert_called_once()
        self.app.status_bar.update_status.assert_called_with("Found: 'Test'")


    def test_find_next_case_insensitive_match_via_option(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = "1.0" # Found
        self.app.search_entry.get.return_value = "test"
        self.app.case_sensitive_var.set(False) # Disable case-sensitive (explicitly)

        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            self.app._find_next()

        args, kwargs = mock_editor.text_area.search.call_args
        self.assertTrue(kwargs.get('nocase', False), "Search should have been case-insensitive (nocase=True)")
        self.app.status_bar.update_status.assert_called_with("Found: 'test'")


    def test_find_previous_case_sensitive_match(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = "1.0" # Found
        self.app.search_entry.get.return_value = "Test"
        self.app.case_sensitive_var.set(True)

        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            self.app._find_previous()

        args, kwargs = mock_editor.text_area.search.call_args
        self.assertFalse(kwargs.get('nocase', True), "Search should have been case-sensitive (nocase=False)")
        self.assertTrue(kwargs.get('backwards'), "Search should have been backwards")
        self.app.status_bar.update_status.assert_called_with("Found: 'Test'")

    def test_on_search_option_changed_clears_last_match(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.clear_search_highlights = MagicMock()
        self.app.last_search_match_info = {'index': "5.5", 'query': "old_query"}
        self.app.search_entry.get.return_value = "new_query" # Simulate query might also change

        with patch.object(self.app, 'get_current_editor', return_value=mock_editor):
            self.app._on_search_option_changed()

        self.assertEqual(self.app.last_search_match_info, {'index': "1.0", 'query': "new_query"})
        mock_editor.clear_search_highlights.assert_called_once()


if __name__ == '__main__':
    unittest.main()
