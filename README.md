# expert-octo-enigma

A Python-based application aiming to replicate core features of Visual Studio Code.

## Currently Implemented Features

- Basic text editing
- File open/save
- Syntax highlighting for Python
- Tabbed Editor Interface: Allows multiple files to be open in different tabs. Includes prompts to save unsaved changes.
- Enhanced File Explorer:
    - Right-click context menu with "New File", "New Folder", "Rename", and "Delete" operations.
    - Recursive directory expansion (view contents of subfolders).
    - Manual refresh option.
- Search Functionality:
    - Basic text search (Find Next/Previous).
    - Case-sensitive search option.
- Status Bar: Displays current file path and other messages.
- UI/UX Refinements:
    - Placeholder icons for files/folders in the File Explorer.
    - Informative status bar messages for search and file operations.

## Planned Features

Refer to the overall project plan for a detailed outline of planned features. This may include:

- Code completion
- Debugging tools
- Version control integration
- Extensibility through plugins
- Advanced Search Options: Regular expression (regex) search.
- File Explorer: Automatic refresh on external file system changes, customizable root directory.
- More robust syntax highlighting for other languages.
- Additional UI/UX refinements (e.g., themes, font settings, drag-and-drop tabs).

## Python 3.13 Compatibility
This application has been tested with Python 3.13.
- All unit tests pass with Python 3.13.4.
- The application launches and basic functionality has been verified.
- A minor adjustment to the test suite (`test_editor.py`) was made to ensure compatibility with mock objects under Python 3.13's testing environment when Tkinter components are patched.
