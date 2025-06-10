import ast
import astor
import os

def fix_path_assertions(filename="test_editor.py"):
    with open(filename, "r") as source:
        tree = ast.parse(source.read())

    has_os_import = False
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    has_os_import = True
                    break
        elif isinstance(node, ast.ImportFrom): # Check for "from os import path" etc.
            if node.module == "os": # Could be specific like 'from os.path import join'
                has_os_import = True # Assume 'os' is available if 'os.path' is used
                break
        if has_os_import:
            break

    if not has_os_import:
        # Try to find a good place to insert, e.g., after other imports or at the top
        insert_pos = 0
        for i, node in enumerate(tree.body):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                insert_pos = i + 1
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.s, str): # Docstring
                insert_pos = i + 1
            else: # Found first non-import, non-docstring line
                if i == 0 and not (isinstance(node, (ast.Import, ast.ImportFrom)) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))):
                    pass # insert at the very top if first line is not import/docstring
                elif insert_pos == 0 and i > 0 : # If no imports found so far, and we are past the first line.
                    pass # keep insert_pos = 0 to insert at top
                elif i > 0 : # general case, insert after last import or docstring
                    pass
                else: # Only if file is empty or only has comments initially
                    pass
                break
        import_os_node = ast.Import(names=[ast.alias(name="os", asname=None)])
        tree.body.insert(insert_pos, import_os_node)
        print("Added 'import os' to the file.")

    class PathFixer(ast.NodeTransformer):
        def _create_os_path_join_node(self, path_parts):
            if not path_parts:
                return ast.Constant(value='')

            args_list = [ast.Constant(value=str(part)) for part in path_parts]

            return ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(value=ast.Name(id="os", ctx=ast.Load()), attr="path", ctx=ast.Load()),
                    attr="join", ctx=ast.Load()
                ),
                args=args_list,
                keywords=[]
            )

        def visit_Call(self, node):
            # Ensure we call generic_visit first to transform children
            super().generic_visit(node) # Process children first

            # Check if it's an assert_called_once_with or assert_called_with call
            if not (isinstance(node.func, ast.Attribute) and \
                    node.func.attr in ["assert_called_once_with", "assert_called_with"]):
                return node

            # Determine the mock object's name for targeting assertions
            mock_obj_name_parts = []
            current_val = node.func.value
            while isinstance(current_val, ast.Attribute):
                mock_obj_name_parts.insert(0, current_val.attr)
                current_val = current_val.value
            if isinstance(current_val, ast.Name):
                mock_obj_name_parts.insert(0, current_val.id)

            mock_obj_full_name = ".".join(mock_obj_name_parts)

            # test_create_new_folder: mock_mkdir.assert_called_once_with('/current/NewFolder')
            if mock_obj_full_name == "mock_mkdir" and len(node.args) == 1 and \
               isinstance(node.args[0], ast.Constant) and node.args[0].value == "/current/NewFolder":
                print("Fixing path for mock_mkdir in test_create_new_folder")
                node.args[0] = self._create_os_path_join_node(["/current", "NewFolder"])

            # test_create_new_file: mock_file_open.assert_called_once_with('/current/new_file.txt', 'w')
            elif mock_obj_full_name == "mock_file_open" and len(node.args) == 2 and \
                 isinstance(node.args[0], ast.Constant) and node.args[0].value == "/current/new_file.txt":
                print("Fixing path for mock_file_open in test_create_new_file")
                node.args[0] = self._create_os_path_join_node(["/current", "new_file.txt"])

            # test_rename_item_file_open_in_app:
            # mock_rename.assert_called_once_with('/fake/old_name.txt', '/fake/renamed_file.txt')
            elif mock_obj_full_name == "mock_rename" and len(node.args) == 2 and \
                 isinstance(node.args[0], ast.Constant) and node.args[0].value == "/fake/old_name.txt" and \
                 isinstance(node.args[1], ast.Constant) and node.args[1].value == "/fake/renamed_file.txt":
                print("Fixing paths for mock_rename in test_rename_item_file_open_in_app")
                node.args[0] = self._create_os_path_join_node(["/fake", "old_name.txt"])
                node.args[1] = self._create_os_path_join_node(["/fake", "renamed_file.txt"])

            # self.mock_app.handle_renamed_file.assert_called_once_with("/fake/old_name.txt", "/fake/renamed_file.txt")
            elif mock_obj_full_name == "self.mock_app.handle_renamed_file" and len(node.args) == 2 and \
                 isinstance(node.args[0], ast.Constant) and node.args[0].value == "/fake/old_name.txt" and \
                 isinstance(node.args[1], ast.Constant) and node.args[1].value == "/fake/renamed_file.txt":
                print("Fixing paths for self.mock_app.handle_renamed_file in test_rename_item_file_open_in_app")
                node.args[0] = self._create_os_path_join_node(["/fake", "old_name.txt"])
                node.args[1] = self._create_os_path_join_node(["/fake", "renamed_file.txt"])

            return node

    transformer = PathFixer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)

    with open(filename, "w") as output:
        output.write(astor.to_source(new_tree))
    print(f"File {filename} modified to use os.path.join in assertions.")

fix_path_assertions()
