# Import the Tkinter library
import tkinter as tk
# Import the Text widget
from tkinter import Text
# Import filedialog for opening and saving files
from tkinter import filedialog
# Import Menu for creating menus
from tkinter import Menu

# --- Global variables that might be accessed by functions ---
# These are initialized here so they can be imported by tests,
# but the actual Tk objects are created only if __name__ == "__main__"
window = None
text_area = None
file_menu = None # Added for completeness, though not directly used in file ops tests
menubar = None # Added for completeness

# --- File Operation Functions ---
# Define the function to open a file
def open_file():
    """Opens a file selected by the user and displays its content in the text area."""
    global text_area, window # Ensure functions use the global (potentially mocked) instances
    try:
        # Ask the user to select a file
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("Text Files", "*.txt"),
                ("Python Files", "*.py"),
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )
        # If no file is selected, filepath will be empty, so do nothing
        if not filepath:
            return
        
        # Open and read the file
        with open(filepath, "r") as input_file:
            text_content = input_file.read()
            
        # Clear the existing content in the text area
        if text_area: # Check if text_area is initialized
            text_area.delete("1.0", tk.END)
        
        # Insert the new content into the text area
        if text_area: # Check if text_area is initialized
            text_area.insert("1.0", text_content)
        
        # Optionally, update the window title to the name of the opened file
        if window: # Check if window is initialized
            window.title(f"Basic Text Editor - {filepath}")
        
    except FileNotFoundError:
        print(f"Error: File not found at the specified path.")
    except Exception as e:
        print(f"An error occurred while opening the file: {e}")

# Define the function to save a file
def save_file():
    """Saves the current content of the text area to a file selected by the user."""
    global text_area, window # Ensure functions use the global (potentially mocked) instances
    try:
        # Ask the user for a filepath to save to
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("Python Files", "*.py"),
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )
        # If no file is selected (user cancels), filepath will be empty, so do nothing
        if not filepath:
            return
        
        # Get the content from the text area
        text_content = ""
        if text_area: # Check if text_area is initialized
            text_content = text_area.get("1.0", tk.END)
        
        # Write the content to the selected file
        with open(filepath, "w") as output_file:
            output_file.write(text_content)
            
        # Optionally, update the window title to the name of the saved file
        if window: # Check if window is initialized
            window.title(f"Basic Text Editor - {filepath}")
        
    except Exception as e:
        print(f"An error occurred while saving the file: {e}")

# --- Main Application Setup and Execution ---
def main_app():
    global window, text_area, file_menu, menubar # Declare globals to assign them

    # Create the main application window
    window = tk.Tk()

    # Set the title of the window
    window.title("Basic Text Editor")

    # --- Menu Bar Setup ---
    # Create the main menu bar
    menubar = Menu(window)
    # Configure the window to use this menu bar
    window.config(menu=menubar)

    # Create the "File" menu
    file_menu = Menu(menubar, tearoff=0) # tearoff=0 removes the tear-off feature

    # Add the "File" menu to the menu bar
    menubar.add_cascade(label="File", menu=file_menu)

    # --- Text Area Setup ---
    # Create a Text widget
    # The widget is parented to the main window
    text_area = Text(window)

    # Configure the Text widget to expand and fill the entire main window
    # expand=True allows the widget to expand if the window is resized
    # fill='both' makes the widget fill the space in both horizontal and vertical directions
    text_area.pack(expand=True, fill='both')

    # Ensure the text area is the main focus for text input when the application starts
    text_area.focus_set()
    
    # --- Populate File Menu ---
    # Add "Open" command
    file_menu.add_command(label="Open", command=open_file)
    # Add "Save" command
    file_menu.add_command(label="Save", command=save_file)
    # Add a separator line
    file_menu.add_separator()
    # Add "Exit" command
    file_menu.add_command(label="Exit", command=window.quit)

    # Start the Tkinter event loop
    # This keeps the window open and responsive to user interactions
    window.mainloop()

if __name__ == "__main__":
    main_app()
