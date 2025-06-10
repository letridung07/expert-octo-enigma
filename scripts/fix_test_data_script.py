import ast
import astor
import os

def fix_rename_test_data(filename="test_editor.py"):
    with open(filename, "r") as source:
        tree = ast.parse(source.read())

    class RenameTestDataFixer(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            # Only target the 'test_rename_item_file_open_in_app' method
            if node.name != "test_rename_item_file_open_in_app":
                # We must call generic_visit for other functions to ensure the whole tree is processed
                return self.generic_visit(node)

            print(f"Visiting function: {node.name}")
            # Traverse the body of this function to find the specific assignment
            # We need to transform the nodes within this function's body
            new_body = []
            for sub_node in node.body:
                if isinstance(sub_node, ast.Assign):
                    # Looking for: self.file_explorer.file_tree.item = MagicMock(...)
                    if len(sub_node.targets) == 1 and \
                       isinstance(sub_node.targets[0], ast.Attribute) and \
                       isinstance(sub_node.targets[0].value, ast.Attribute) and \
                       sub_node.targets[0].value.attr == "file_tree" and \
                       sub_node.targets[0].attr == "item":

                        if isinstance(sub_node.value, ast.Call) and \
                           isinstance(sub_node.value.func, ast.Name) and \
                           sub_node.value.func.id == "MagicMock":

                            # Check for return_value={"values": ["/fake/old_name.txt", "file"]}
                            for kw_idx, kw in enumerate(sub_node.value.keywords):
                                if kw.arg == "return_value" and isinstance(kw.value, ast.Dict):
                                    for i, key_node in enumerate(kw.value.keys):
                                        if isinstance(key_node, ast.Constant) and key_node.value == "values":
                                            value_node = kw.value.values[i]
                                            if isinstance(value_node, ast.List) and len(value_node.elts) == 2 and \
                                               isinstance(value_node.elts[0], ast.Constant) and \
                                               value_node.elts[0].value == "/fake/old_name.txt":

                                                print(f"Found target assignment in {node.name}. Modifying old_path setup.")
                                                # Create the new os.path.join node
                                                new_path_node = ast.Call(
                                                    func=ast.Attribute(
                                                        value=ast.Attribute(value=ast.Name(id="os", ctx=ast.Load()), attr="path", ctx=ast.Load()),
                                                        attr="join", ctx=ast.Load()
                                                    ),
                                                    args=[ast.Constant(value="/fake"), ast.Constant(value="old_name.txt")],
                                                    keywords=[]
                                                )
                                                # Replace the old path string constant with the new node
                                                value_node.elts[0] = new_path_node
                                                print(f"Successfully modified old_path in {node.name}")
                                            break
                            # No break here, continue checking other assignments if any (though unlikely for this specific case)
                new_body.append(sub_node) # Keep the (possibly modified) node
            node.body = new_body # Assign the new body back to the function
            return node # Return the modified function node

    transformer = RenameTestDataFixer()
    new_tree = transformer.visit(tree) # Apply the transformation to the whole tree
    ast.fix_missing_locations(new_tree) # Important for any new nodes

    with open(filename, "w") as output:
        output.write(astor.to_source(new_tree))
    print(f"File {filename} potentially modified to fix test_rename_item_file_open_in_app data.")

fix_rename_test_data()
