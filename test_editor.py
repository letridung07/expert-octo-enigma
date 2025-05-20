import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tkinter as tk # Required for tk.END

# Import functions and global variables from main.py
# It's important that main.py is structured to allow this without running the UI
# We will patch main.window and main.text_area
import main

class TestEditorFileOperations(unittest.TestCase):

    def setUp(self):
        # Create a dummy Tk root window for the tests, as some tk constants might need it.
        # This window will not be shown or enter mainloop.
        self.test_root = tk.Tk() 
        # It's good practice to explicitly set the global references in main to mocks
        # for each test, or ensure they are reset.
        main.window = MagicMock()
        main.text_area = MagicMock()
        # Configure the mock text_area's get method for save tests
        main.text_area.get.return_value = "Sample content to save."
        # Configure the mock text_area's delete and insert methods for open tests
        # These don't need specific return values, just to be callable.

    def tearDown(self):
        # Destroy the dummy root window
        self.test_root.destroy()
        # Clean up any files created during tests, if necessary
        if os.path.exists("test_output.txt"):
            os.remove("test_output.txt")
        if os.path.exists("test_input.txt"):
            os.remove("test_input.txt")

    @patch('main.filedialog.asksaveasfilename')
    def test_save_functionality(self, mock_asksaveasfilename):
        # Configure mocks
        mock_asksaveasfilename.return_value = "test_output.txt"
        
        # Mock builtins.open for file writing
        m_open = mock_open()
        with patch('builtins.open', m_open):
            main.save_file()

        # Assertions
        mock_asksaveasfilename.assert_called_once_with(
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("Python Files", "*.py"),
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )
        main.text_area.get.assert_called_once_with("1.0", tk.END)
        m_open.assert_called_once_with("test_output.txt", "w")
        m_open().write.assert_called_once_with("Sample content to save.")
        main.window.title.assert_called_once_with("Basic Text Editor - test_output.txt")

    @patch('main.filedialog.askopenfilename')
    def test_open_functionality(self, mock_askopenfilename):
        # Prepare a dummy input file
        test_input_content = "Sample content to open."
        with open("test_input.txt", "w") as f:
            f.write(test_input_content)
        
        # Configure mocks
        mock_askopenfilename.return_value = "test_input.txt"

        # Call the function
        main.open_file()

        # Assertions
        mock_askopenfilename.assert_called_once_with(
            filetypes=[
                ("Text Files", "*.txt"),
                ("Python Files", "*.py"),
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )
        main.text_area.delete.assert_called_once_with("1.0", tk.END)
        main.text_area.insert.assert_called_once_with("1.0", test_input_content)
        main.window.title.assert_called_once_with("Basic Text Editor - test_input.txt")

    def test_save_file_no_filepath(self,):
        # Test case where user cancels the save dialog
        with patch('main.filedialog.asksaveasfilename', return_value="") as mock_dialog, \
             patch('builtins.open', new_callable=mock_open) as mock_open_call:
            main.save_file()
            mock_dialog.assert_called_once()
            main.text_area.get.assert_not_called() # Should not try to get text
            mock_open_call.assert_not_called() # Should not try to open file
            main.window.title.assert_not_called() # Should not change title

    def test_open_file_no_filepath(self):
        # Test case where user cancels the open dialog
        with patch('main.filedialog.askopenfilename', return_value="") as mock_dialog, \
             patch('builtins.open', new_callable=mock_open) as mock_open_call: # Though open isn't directly called if no path
            main.open_file()
            mock_dialog.assert_called_once()
            main.text_area.delete.assert_not_called() # Should not try to delete text
            main.text_area.insert.assert_not_called() # Should not try to insert text
            mock_open_call.assert_not_called() # Should not try to open file
            main.window.title.assert_not_called() # Should not change title


if __name__ == '__main__':
    unittest.main()
