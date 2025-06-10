import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import tkinter as tk
from tkinter import ttk # Required for Treeview

# Import classes from main.py
from main import App, TextEditor, FileExplorer, StatusBar, SYNTAX_RULES

class TestStatusBar(unittest.TestCase):
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
        self.status_bar.update_filepath(None)
        self.assertEqual(self.status_bar.label.cget("text"), "Ready")


class TestTextEditor(unittest.TestCase):
    def setUp(self):
        self.test_root = tk.Tk()
        # Mock StatusBar for TextEditor
        self.mock_status_bar_frame = tk.Frame(self.test_root)
        self.mock_status_bar = MagicMock(spec=StatusBar)

        self.text_editor_frame = tk.Frame(self.test_root)
        self.text_editor = TextEditor(self.text_editor_frame, self.mock_status_bar)
        # Ensure text_area is created
        self.assertIsNotNone(self.text_editor.text_area)

    def tearDown(self):
        self.test_root.destroy()

    def test_set_get_content(self):
        test_content = "Hello, world!"
        self.text_editor.set_content(test_content, apply_highlighting=False) # Disable highlighting for this test
        self.assertEqual(self.text_editor.get_content().strip(), test_content.strip()) # Strip to remove potential newline
        self.text_editor.clear_content()
        self.assertEqual(self.text_editor.get_content().strip(), "")

    @patch('main.re.finditer') # Patch re.finditer used by apply_syntax_highlighting
    def test_apply_syntax_highlighting_keywords(self, mock_finditer):
        # Simulate a match for a keyword
        mock_match = MagicMock()
        mock_match.start.return_value = 0
        mock_match.end.return_value = 3 # "def"
        mock_finditer.return_value = [mock_match] # Simulate finding one "def"

        # Mock tag_add and tag_remove
        self.text_editor.text_area.tag_add = MagicMock()
        self.text_editor.text_area.tag_remove = MagicMock()

        self.text_editor.set_content("def func(): pass", apply_highlighting=False) # Set content first
        self.text_editor.apply_syntax_highlighting() # Manually trigger

        # Check tag_remove calls
        expected_remove_calls = [call(tag_name, "1.0", tk.END) for tag_name, _ in SYNTAX_RULES]
        self.text_editor.text_area.tag_remove.assert_has_calls(expected_remove_calls, any_order=True)

        # Check that finditer was called for the keyword pattern
        keyword_pattern = next(p for t, p in SYNTAX_RULES if t == "keyword")
        mock_finditer.assert_any_call(keyword_pattern, "def func(): pass\n", 0)

        # Check tag_add was called for the keyword
        self.text_editor.text_area.tag_add.assert_any_call("keyword", "1.0", "1.3")


    def test_apply_syntax_highlighting_comments(self):
        self.text_editor.text_area.tag_add = MagicMock()
        self.text_editor.text_area.tag_remove = MagicMock()

        test_code = "# This is a comment\nprint('Hello')"
        self.text_editor.set_content(test_code, apply_highlighting=False)
        self.text_editor.apply_syntax_highlighting()

        # Expected: tag_add("comment", "1.0", "1.19")
        # Need to check if tag_add was called with arguments that include "comment"
        # and the correct range for the comment.
        args_list = self.text_editor.text_area.tag_add.call_args_list
        found_comment_tag = False
        for c in args_list:
            if c[0][0] == "comment" and c[0][1] == "1.0" and c[0][2] == "1.19": # "1.19" is end of "# This is a comment"
                found_comment_tag = True
                break
        self.assertTrue(found_comment_tag, "Comment tag not applied correctly")


    def test_apply_syntax_highlighting_strings(self):
        self.text_editor.text_area.tag_add = MagicMock()
        self.text_editor.text_area.tag_remove = MagicMock()

        test_code = "text = \"Hello World\" # a comment"
        self.text_editor.set_content(test_code, apply_highlighting=False)
        self.text_editor.apply_syntax_highlighting()
        
        args_list = self.text_editor.text_area.tag_add.call_args_list
        found_string_tag = False
        # Expected: "string", "1.7", "1.20" for "Hello World"
        for c in args_list:
            if c[0][0] == "string" and c[0][1] == "1.7" and c[0][2] == "1.20":
                found_string_tag = True
                break
        self.assertTrue(found_string_tag, "String tag not applied correctly for double quotes")


class TestFileExplorer(unittest.TestCase):
    def setUp(self):
        self.test_root = tk.Tk()
        self.mock_text_editor = MagicMock(spec=TextEditor)
        self.mock_app = MagicMock(spec=App) # Mock App instance

        self.file_explorer_frame = tk.Frame(self.test_root)
        self.file_explorer = FileExplorer(self.file_explorer_frame, self.mock_text_editor, self.mock_app)
        self.assertIsNotNone(self.file_explorer.file_tree)

    def tearDown(self):
        self.test_root.destroy()

    @patch('os.listdir')
    @patch('os.path.join', side_effect=lambda *args: "/".join(args)) # Simple mock for os.path.join
    @patch('os.path.isdir', side_effect=lambda x: "dir" in x) # Mock isdir
    def test_populate_file_explorer(self, mock_isdir, mock_join, mock_listdir):
        mock_listdir.return_value = ["file1.txt", "subdir", "file2.py"]
        self.file_explorer.file_tree.insert = MagicMock() # Mock the treeview's insert method

        self.file_explorer.populate_file_explorer("/fake/path")

        mock_listdir.assert_called_once_with("/fake/path")

        expected_calls = [
            call('', 'end', text="file1.txt", values=["/fake/path/file1.txt"]),
            call('', 'end', text="subdir", values=["/fake/path/subdir"]),
            call('', 'end', text="file2.py", values=["/fake/path/file2.py"]),
        ]
        self.file_explorer.file_tree.insert.assert_has_calls(expected_calls, any_order=True)

    @patch('builtins.open', new_callable=mock_open, read_data="file content")
    @patch('os.path.isfile', return_value=True)
    def test_on_file_select_opens_file(self, mock_isfile, mock_file_open):
        # Simulate selection in Treeview
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I001",)) # Dummy item ID
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/path/file.txt"]})

        self.file_explorer._on_file_select() # Trigger the handler

        mock_isfile.assert_called_once_with("/fake/path/file.txt")
        mock_file_open.assert_called_once_with("/fake/path/file.txt", "r")
        self.mock_text_editor.set_content.assert_called_once_with("file content")
        self.mock_app.update_title_and_status.assert_called_once_with("/fake/path/file.txt")

    @patch('os.path.isfile', return_value=False) # Item selected is a directory
    def test_on_file_select_directory(self, mock_isfile):
        self.file_explorer.file_tree.selection = MagicMock(return_value=("I002",))
        self.file_explorer.file_tree.item = MagicMock(return_value={"values": ["/fake/path/folder"]})

        self.file_explorer._on_file_select()

        mock_isfile.assert_called_once_with("/fake/path/folder")
        self.mock_text_editor.set_content.assert_not_called()
        self.mock_app.update_title_and_status.assert_not_called()


class TestApp(unittest.TestCase):
    def setUp(self):
        # Patch the App's __init__ to prevent it from creating a real Tk window during test setup
        # We will test methods individually, mocking dependencies
        with patch('tkinter.Tk', MagicMock()): # Patch Tk() if App tries to create it early
            self.app = App()

        # Manually create and assign mocks for components App would normally create
        self.app.window = MagicMock(spec=tk.Tk) # Mock the main window
        self.app.text_editor = MagicMock(spec=TextEditor)
        self.app.status_bar = MagicMock(spec=StatusBar)
        self.app.file_explorer = MagicMock(spec=FileExplorer) # Though not directly used in these tests

    def test_update_title_and_status(self):
        self.app.update_title_and_status("test_file.py")
        self.app.window.title.assert_called_once_with("Basic Text Editor - test_file.py")
        self.app.status_bar.update_filepath.assert_called_once_with("test_file.py")

        self.app.window.title.reset_mock()
        self.app.status_bar.update_filepath.reset_mock()
        self.app.status_bar.update_status = MagicMock() # also mock update_status for the None case

        self.app.update_title_and_status(None)
        self.app.window.title.assert_called_once_with("Basic Text Editor - Refactored")
        self.app.status_bar.update_status.assert_called_once_with("Ready")


    @patch('main.filedialog.askopenfilename')
    @patch('builtins.open', new_callable=mock_open, read_data="Opened content")
    def test_open_file_functionality(self, mock_open_call, mock_askopenfilename):
        mock_askopenfilename.return_value = "/fake/path/opened_file.txt"
        
        self.app.open_file()

        mock_askopenfilename.assert_called_once()
        self.app.text_editor.set_content.assert_called_once_with("Opened content")
        self.app.window.title.assert_called_once_with("Basic Text Editor - /fake/path/opened_file.txt")
        self.app.status_bar.update_filepath.assert_called_once_with("/fake/path/opened_file.txt")

    @patch('main.filedialog.asksaveasfilename')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_file_functionality(self, mock_open_call, mock_asksaveasfilename):
        mock_asksaveasfilename.return_value = "/fake/path/saved_file.txt"
        self.app.text_editor.get_content.return_value = "Content to save"

        self.app.save_file()

        mock_asksaveasfilename.assert_called_once()
        self.app.text_editor.get_content.assert_called_once()
        mock_open_call.assert_called_once_with("/fake/path/saved_file.txt", "w")
        mock_open_call().write.assert_called_once_with("Content to save")
        self.app.window.title.assert_called_once_with("Basic Text Editor - /fake/path/saved_file.txt")
        self.app.status_bar.update_filepath.assert_called_once_with("/fake/path/saved_file.txt")

    def test_open_file_no_filepath(self):
        with patch('main.filedialog.askopenfilename', return_value="") as mock_dialog:
            self.app.open_file()
            mock_dialog.assert_called_once()
            self.app.text_editor.set_content.assert_not_called()
            self.app.window.title.assert_not_called() # Title update is part of update_title_and_status
            self.app.status_bar.update_filepath.assert_not_called()

    def test_save_file_no_filepath(self):
         with patch('main.filedialog.asksaveasfilename', return_value="") as mock_dialog:
            self.app.save_file()
            mock_dialog.assert_called_once()
            self.app.text_editor.get_content.assert_not_called()
            # No file write should be attempted, title not changed, status not changed
            self.app.window.title.assert_not_called()
            self.app.status_bar.update_filepath.assert_not_called()


if __name__ == '__main__':
    unittest.main()
