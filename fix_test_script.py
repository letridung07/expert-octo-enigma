import ast
import astor # Requires: pip install astor

def fix_test_populate_assigns_icons(filename="test_editor.py"):
    with open(filename, "r") as source:
        tree = ast.parse(source.read())

    class Visitor(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            # Check if this is the function we're interested in
            if node.name == "test_populate_assigns_icons":
                # Traverse the body of this function
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, ast.Assign):
                        for target in sub_node.targets:
                            if isinstance(target, ast.Name) and target.id in ["mock_folder_icon_instance", "mock_file_icon_instance"]:
                                if isinstance(sub_node.value, ast.Call):
                                    # Check for direct MagicMock call or from unittest.mock.MagicMock
                                    is_magic_mock_call = False
                                    if isinstance(sub_node.value.func, ast.Name) and sub_node.value.func.id == "MagicMock":
                                        is_magic_mock_call = True
                                    elif isinstance(sub_node.value.func, ast.Attribute) and                                          isinstance(sub_node.value.func.value, ast.Name) and                                          sub_node.value.func.value.id == "mock" and                                          sub_node.value.func.attr == "MagicMock": # for unittest.mock.MagicMock
                                        is_magic_mock_call = True
                                    elif isinstance(sub_node.value.func, ast.Attribute) and                                          sub_node.value.func.attr == "MagicMock": # for direct attribute call if MagicMock is imported differently
                                         is_magic_mock_call = True


                                    if is_magic_mock_call:
                                        # Check if spec=tk.PhotoImage is present and remove it
                                        new_keywords = []
                                        modified = False
                                        for kw in sub_node.value.keywords:
                                            is_spec_photoimage = False
                                            if kw.arg == "spec":
                                                if isinstance(kw.value, ast.Attribute) and                                                    isinstance(kw.value.value, ast.Name) and                                                    kw.value.value.id == "tk" and                                                    kw.value.attr == "PhotoImage":
                                                    is_spec_photoimage = True
                                                elif isinstance(kw.value, ast.Name) and                                                      kw.value.id == "PhotoImage": # If PhotoImage is imported directly
                                                     is_spec_photoimage = True

                                            if not is_spec_photoimage:
                                                new_keywords.append(kw)
                                            else:
                                                modified = True

                                        if modified:
                                            sub_node.value.keywords = new_keywords
            return node

    transformer = Visitor()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree) # Important!

    with open(filename, "w") as output:
        output.write(astor.to_source(new_tree))
    print(f"File {filename} potentially modified.")

fix_test_populate_assigns_icons()
