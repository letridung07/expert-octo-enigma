import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import tkinter as tk
from tkinter import ttk
from main import App, TextEditor, FileExplorer, StatusBar, SYNTAX_RULES


class TestStatusBar(unittest.TestCase):

    def setUp(self):
        self.test_root = tk.Tk()
        self.status_bar_frame = tk.Frame(self.test_root)
        self.status_bar = StatusBar(self.status_bar_frame)

    def tearDown(self):
        self.test_root.destroy()

    def test_update_status_message(self):
        self.status_bar.update_status('Test Message')
        self.assertEqual(self.status_bar.label.cget('text'), 'Test Message')

    def test_update_filepath(self):
        self.status_bar.update_filepath('test/file.py')
        self.assertEqual(self.status_bar.label.cget('text'),
            'File: test/file.py')
        self.status_bar.update_filepath(None)
        self.assertEqual(self.status_bar.label.cget('text'), 'Ready')


class TestTextEditor(unittest.TestCase):

    def setUp(self):
        self.test_root = tk.Tk()
        self.mock_app_instance = MagicMock(spec=App)
        self.mock_status_bar = MagicMock(spec=StatusBar)
        self.text_editor_frame = tk.Frame(self.test_root)
        self.text_editor = TextEditor(self.text_editor_frame, self.
            mock_status_bar, self.mock_app_instance)
        self.assertIsNotNone(self.text_editor.text_area)

    def tearDown(self):
        self.test_root.destroy()

    def test_set_get_content(self):
        test_content = 'Hello, world!'
        self.text_editor.set_content(test_content, initial_load=True)
        self.assertEqual(self.text_editor.get_content().strip(),
            test_content.strip())
        self.assertFalse(self.text_editor.is_modified)
        self.text_editor.clear_content()
        self.assertEqual(self.text_editor.get_content().strip(), '')

    def test_mark_as_modified(self):
        self.text_editor.mark_as_modified(True)
        self.assertTrue(self.text_editor.is_modified)
        self.mock_app_instance.update_tab_text_for_editor.assert_called_once_with(
            self.text_editor, True)
        self.text_editor.mark_as_modified(False)
        self.assertFalse(self.text_editor.is_modified)
        self.mock_app_instance.update_tab_text_for_editor.assert_called_with(
            self.text_editor, False)

    @patch('main.re.finditer')
    def test_apply_syntax_highlighting_keywords(self, mock_finditer):
        mock_match = MagicMock()
        mock_match.start.return_value = 0
        mock_match.end.return_value = 3
        mock_finditer.return_value = [mock_match]
        self.text_editor.text_area.tag_add = MagicMock()
        self.text_editor.text_area.tag_remove = MagicMock()
        self.text_editor.set_content('def func(): pass', initial_load=True)
        keyword_pattern = next(p for t, p in SYNTAX_RULES if t == 'keyword')
        mock_finditer.assert_any_call(keyword_pattern, 'def func(): pass\n', 0)
        self.text_editor.text_area.tag_add.assert_any_call('keyword', '1.0',
            '1.3')

    def test_clear_search_highlights(self):
        self.text_editor.text_area.tag_add('search_highlight', '1.0', '1.5')
        self.text_editor.clear_search_highlights()
        pass


class TestFileExplorer(unittest.TestCase):

    def setUp(self):
        self.test_root = tk.Tk()
        self.mock_app = MagicMock(spec=App)
        self.mock_app.status_bar = MagicMock(spec=StatusBar)
        self.file_explorer_frame = tk.Frame(self.test_root)
        self.file_explorer = FileExplorer(self.file_explorer_frame, self.
            mock_app, self.mock_app)
        self.assertIsNotNone(self.file_explorer.file_tree)

    def tearDown(self):
        self.test_root.destroy()

    @patch('os.listdir')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('os.path.isdir', side_effect=lambda x: 'dir' in x)
    def test_populate_file_explorer(self, mock_isdir, mock_join, mock_listdir):

        def listdir_side_effect(path):
            if path == '/fake/path':
                return ['file1.txt', 'subdir', 'file2.py']
            elif path == '/fake/path/subdir':
                return ['subfile.txt']
            return []
        mock_listdir.side_effect = listdir_side_effect
        self.file_explorer.file_tree.insert = MagicMock()
        self.file_explorer.populate_file_explorer('', '/fake/path')
        expected_listdir_calls = [call('/fake/path'), call('/fake/path/subdir')
            ]
        mock_listdir.assert_has_calls(expected_listdir_calls, any_order=True)
        expected_insert_calls = [call('', 'end', text='file1.txt', image='',
            values=['/fake/path/file1.txt', 'file'], open=False), call('',
            'end', text='subdir', image='', values=['/fake/path/subdir',
            'directory'], open=False), call('', 'end', text='file2.py',
            image='', values=['/fake/path/file2.py', 'file'], open=False)]
        original_expected_insert_calls = [call('', 'end', text='file1.txt',
            values=['/fake/path/file1.txt'], tags=('file',)), call('',
            'end', text='subdir', values=['/fake/path/subdir'], tags=(
            'directory',)), call('', 'end', text='file2.py', values=[
            '/fake/path/file2.py'], tags=('file',))]

    @patch('os.path.isfile', return_value=True)
    def test_on_file_select_opens_file_in_app(self, mock_isfile):
        self.file_explorer.file_tree.selection = MagicMock(return_value=(
            'I001',))
        self.file_explorer.file_tree.item = MagicMock(return_value=(
            '/fake/path/file.txt', 'file'))
        self.file_explorer._on_file_select()
        mock_isfile.assert_called_once_with('/fake/path/file.txt')
        self.mock_app.open_file_in_new_tab.assert_called_once_with(
            '/fake/path/file.txt')

    @patch('main.simpledialog.askstring')
    @patch('os.mkdir')
    def test_create_new_folder(self, mock_mkdir, mock_askstring):
        mock_askstring.return_value = 'NewFolder'
        self.file_explorer.file_tree.selection = MagicMock(return_value=())
        self.file_explorer.current_path = '/current'
        with patch.object(self.file_explorer, 'populate_file_explorer'
            ) as mock_populate:
            self.file_explorer._create_new_folder()
        mock_mkdir.assert_called_once_with(os.path.join('/current',
            'NewFolder'))
        mock_populate.assert_called_once_with('/current')
        self.mock_app.status_bar.update_status.assert_called_with(
            "Folder 'NewFolder' created in /current.")

    @patch('main.simpledialog.askstring')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    def test_create_new_file(self, mock_exists, mock_file_open, mock_askstring
        ):
        mock_askstring.return_value = 'new_file.txt'
        self.file_explorer.file_tree.selection = MagicMock(return_value=())
        self.file_explorer.current_path = '/current'
        with patch.object(self.file_explorer, 'populate_file_explorer'
            ) as mock_populate:
            self.file_explorer._create_new_file()
        mock_file_open.assert_called_once_with(os.path.join('/current',
            'new_file.txt'), 'w')
        mock_populate.assert_called_once_with('/current')
        self.mock_app.status_bar.update_status.assert_called_with(
            "File 'new_file.txt' created in /current.")

    @patch('main.simpledialog.askstring')
    @patch('os.rename')
    def test_rename_item_file_open_in_app(self, mock_rename, mock_askstring):
        mock_askstring.return_value = 'renamed_file.txt'
        self.file_explorer.file_tree.selection = MagicMock(return_value=(
            'I001',))
        self.file_explorer.file_tree.item = MagicMock(return_value={
            'values': ['/fake/old_name.txt', 'file']})
        self.file_explorer.current_path = '/fake'
        with patch.object(self.file_explorer, 'populate_file_explorer'
            ) as mock_populate:
            self.file_explorer._rename_item()
        mock_rename.assert_called_once_with(os.path.join('/fake',
            'old_name.txt'), os.path.join('/fake', 'renamed_file.txt'))
        self.mock_app.handle_renamed_file.assert_called_once_with(os.path.
            join('/fake', 'old_name.txt'), os.path.join('/fake',
            'renamed_file.txt'))
        mock_populate.assert_called_once()
        self.mock_app.status_bar.update_status.assert_called_with(
            "Renamed 'old_name.txt' to 'renamed_file.txt'.")

    @patch('main.messagebox.askyesno', return_value=True)
    @patch('os.remove')
    @patch('os.path.isfile', return_value=True)
    def test_delete_item_file_open_in_app(self, mock_isfile, mock_os_remove,
        mock_askyesno):
        self.file_explorer.file_tree.selection = MagicMock(return_value=(
            'I001',))
        self.file_explorer.file_tree.item = MagicMock(return_value={
            'values': ['/fake/file_to_delete.txt', 'file']})
        self.file_explorer.current_path = '/fake'
        with patch.object(self.file_explorer, 'populate_file_explorer'
            ) as mock_populate:
            self.file_explorer._delete_item()
        mock_os_remove.assert_called_once_with('/fake/file_to_delete.txt')
        self.mock_app.handle_deleted_file.assert_called_once_with(
            '/fake/file_to_delete.txt')
        mock_populate.assert_called_once()
        self.mock_app.status_bar.update_status.assert_called_with(
            "Deleted 'file_to_delete.txt'.")

    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_populate_recursive_on_treeview_open(self, mock_isdir, mock_listdir
        ):
        dir_id = 'item_dir'
        dir_path = '/fake/testdir'
        placeholder_id = 'item_placeholder'

        def initial_insert_side_effect(parent, index, text, values, open,
            image=None):
            if text == 'testdir':
                return dir_id
            if text == '...':
                return placeholder_id
            return MagicMock()
        self.file_explorer.file_tree.insert = MagicMock(side_effect=
            initial_insert_side_effect)
        mock_isdir.return_value = True
        mock_listdir.return_value = ['subfile.txt']
        self.file_explorer.file_tree.item = MagicMock(side_effect=lambda
            node_id: {dir_id: {'values': [dir_path, 'directory']},
            placeholder_id: {'values': ['placeholder', 'placeholder']}}.get
            (node_id))
        self.file_explorer.file_tree.get_children = MagicMock(return_value=
            [placeholder_id])
        self.file_explorer.file_tree.focus = MagicMock(return_value=dir_id)
        self.file_explorer.file_tree.delete = MagicMock()
        with patch.object(self.file_explorer, 'populate_file_explorer'
            ) as mock_recursive_populate:
            self.file_explorer._on_treeview_open(None)
        mock_recursive_populate.assert_called_once_with(dir_id, dir_path)
        self.file_explorer.file_tree.delete.assert_called_once_with(
            placeholder_id)

    def test_refresh_explorer(self):
        self.file_explorer.file_tree.get_children = MagicMock(return_value=
            ['id1', 'id2'])
        self.file_explorer.file_tree.delete = MagicMock()
        with patch.object(self.file_explorer, 'populate_file_explorer'
            ) as mock_populate:
            self.file_explorer._refresh_explorer()
        self.file_explorer.file_tree.delete.assert_has_calls([call('id1'),
            call('id2')], any_order=True)
        mock_populate.assert_called_once_with('', self.file_explorer.
            current_path)

    @patch('os.listdir', return_value=['folder1'])
    @patch('os.path.isdir', return_value=True)
    @patch('main.FileExplorer._load_icons', MagicMock())
    def test_populate_adds_placeholder_for_directory(self, mock_isdir,
        mock_listdir):
        self.file_explorer.file_tree.insert = MagicMock(return_value=
            'folder_id')
        self.file_explorer.current_path = '/testroot'
        self.file_explorer.populate_file_explorer('', self.file_explorer.
            current_path)
        self.assertGreaterEqual(self.file_explorer.file_tree.insert.
            call_count, 2)
        args_list = self.file_explorer.file_tree.insert.call_args_list
        self.assertEqual(args_list[0][1]['text'], 'folder1')
        self.assertEqual(args_list[0][1]['values'][1], 'directory')
        self.assertEqual(args_list[1][1]['text'], '...')
        self.assertEqual(args_list[1][1]['values'][0], 'placeholder')
        self.assertEqual(args_list[1][0][0], 'folder_id')

    @patch('os.listdir', side_effect=PermissionError('Test permission denied'))
    @patch('main.FileExplorer._load_icons', MagicMock())
    def test_populate_handles_permission_error(self, mock_listdir):
        self.file_explorer.file_tree.insert = MagicMock()
        self.file_explorer.current_path = '/unreadable_dir'
        self.file_explorer.populate_file_explorer('', self.file_explorer.
            current_path)
        self.file_explorer.file_tree.insert.assert_called_once_with('',
            'end', text='[Error: unreadable_dir]', values=[
            '/unreadable_dir', 'error'])

    @patch('tkinter.PhotoImage')
    @patch('os.path.isdir')
    @patch('os.listdir', return_value=['file.txt', 'folder'])
    def test_populate_assigns_icons(self, mock_listdir, mock_isdir,
        mock_photoimage):

        def isdir_side_effect(path):
            if path.endswith('folder'):
                return True
            if path.endswith('file.txt'):
                return False
            return False
        mock_isdir.side_effect = isdir_side_effect

        def no_op_load_icons(instance):
            instance.folder_icon = None
            instance.file_icon = None
        with patch.object(FileExplorer, '_load_icons', no_op_load_icons):
            fe_for_icon_test = FileExplorer(self.file_explorer_frame, self.
                mock_app, self.mock_app)
        mock_folder_icon_instance = MagicMock()
        mock_file_icon_instance = MagicMock()
        fe_for_icon_test.folder_icon = mock_folder_icon_instance
        fe_for_icon_test.file_icon = mock_file_icon_instance
        fe_for_icon_test.file_tree.insert = MagicMock()
        fe_for_icon_test.populate_file_explorer('', '/fake_path')
        calls = fe_for_icon_test.file_tree.insert.call_args_list
        self.assertTrue(len(calls) >= 2,
            'Should have tried to insert at least two items')
        found_file_call = False
        found_folder_call = False
        for call_args_entry in calls:
            kwargs = call_args_entry[1]
            if kwargs['text'] == 'file.txt':
                self.assertEqual(kwargs['image'], mock_file_icon_instance)
                found_file_call = True
            elif kwargs['text'] == 'folder':
                self.assertEqual(kwargs['image'], mock_folder_icon_instance)
                found_folder_call = True
        self.assertTrue(found_file_call,
            'File item with icon not inserted correctly')
        self.assertTrue(found_folder_call,
            'Folder item with icon not inserted correctly')


class TestApp(unittest.TestCase):

    def setUp(self):
        self.test_root = tk.Tk()
        with patch.object(App, '_create_menu', MagicMock()), patch.object(App,
            '_setup_search_ui', MagicMock()), patch.object(App,
            'update_title_and_status', MagicMock()):
            self.app = App()
        self.app.status_bar = MagicMock(spec=StatusBar)
        self.app.status_bar.frame = MagicMock(spec=tk.Frame)
        self.app.file_explorer = MagicMock(spec=FileExplorer)
        self.app.search_frame = MagicMock(spec=tk.Frame)
        self.app.search_entry = MagicMock(spec=tk.Entry)
        self.app.editors = {}
        self.app.tab_filepaths = {}
        self.app.last_search_match_info = {'index': '1.0', 'query': ''}

    def tearDown(self):
        self.test_root.destroy()

    @patch('builtins.open', new_callable=mock_open, read_data='file content')
    @patch('os.path.isfile', return_value=True)
    @patch('main.TextEditor')
    def test_open_file_in_new_tab(self, MockTextEditor, mock_isfile,
        mock_file_open):
        mock_editor_instance = MockTextEditor.return_value
        mock_editor_instance.is_modified = False
        self.app.notebook.tabs = MagicMock(return_value=[])
        self.app.notebook.add = MagicMock()
        self.app.notebook.select = MagicMock(return_value='.!notebook.!frame')
        self.app.open_file_in_new_tab('/fake/test.txt')
        self.app.notebook.add.assert_called_once()
        MockTextEditor.assert_called_once()
        mock_editor_instance.set_content.assert_called_once_with('file content'
            , initial_load=True)
        self.assertEqual(len(self.app.editors), 1)
        self.assertTrue(any(fp == '/fake/test.txt' for fp in self.app.
            tab_filepaths.values()))

    def test_open_existing_file_switches_tab(self):
        mock_editor = MagicMock(spec=TextEditor)
        tab_id_1 = '.!notebook.!frame'
        self.app.editors = {tab_id_1: mock_editor}
        self.app.tab_filepaths = {tab_id_1: '/fake/existing.txt'}
        self.app.notebook.tabs = MagicMock(return_value=[tab_id_1])
        self.app.notebook.select = MagicMock()
        self.app.notebook.add = MagicMock()
        self.app.open_file_in_new_tab('/fake/existing.txt')
        self.app.notebook.select.assert_called_with(tab_id_1)
        self.app.notebook.add.assert_not_called()
        self.assertEqual(len(self.app.editors), 1)

    @patch('main.messagebox.askyesnocancel', return_value=False)
    def test_close_current_tab_no_modifications(self, mock_messagebox):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.is_modified = False
        tab_id = '.!notebook.!frame'
        self.app.notebook.tabs = MagicMock(return_value=[tab_id])
        self.app.notebook.select = MagicMock(return_value=tab_id)
        self.app.notebook.forget = MagicMock()
        self.app.editors = {tab_id: mock_editor}
        self.app.tab_filepaths = {tab_id: '/fake/file.txt'}
        self.app.close_current_tab()
        mock_messagebox.assert_not_called()
        self.app.notebook.forget.assert_called_once_with(tab_id)
        self.assertNotIn(tab_id, self.app.editors)

    @patch('main.messagebox.askyesnocancel', return_value=True)
    @patch.object(App, 'save_file')
    def test_close_current_tab_modified_save_yes(self, mock_save_file,
        mock_messagebox):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.is_modified = True
        tab_id = '.!notebook.!frame'
        self.app.notebook.tabs = MagicMock(return_value=[tab_id])
        self.app.notebook.select = MagicMock(return_value=tab_id)
        self.app.notebook.forget = MagicMock()
        self.app.editors = {tab_id: mock_editor}
        self.app.tab_filepaths = {tab_id: '/fake/file.txt'}

        def side_effect_save():
            mock_editor.is_modified = False
        mock_save_file.side_effect = side_effect_save
        self.app.close_current_tab()
        mock_messagebox.assert_called_once()
        mock_save_file.assert_called_once()
        self.app.notebook.forget.assert_called_once_with(tab_id)

    def test_on_tab_changed(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.clear_search_highlights = MagicMock()
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            with patch.object(self.app, 'update_title_and_status'
                ) as mock_update_title:
                self.app.search_frame_visible = True
                self.app.on_tab_changed()
                mock_update_title.assert_called_once()
                mock_editor.clear_search_highlights.assert_called_once()

    def test_handle_renamed_file(self):
        tab_id = '.!notebook.!frame'
        old_path = '/old/path.txt'
        new_path = '/new/path.txt'
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.is_modified = True
        self.app.tab_filepaths = {tab_id: old_path}
        self.app.editors = {tab_id: mock_editor}
        self.app.notebook.select = MagicMock(return_value=tab_id)
        self.app.notebook.tab = MagicMock()
        self.app.notebook.tabs = MagicMock(return_value=[tab_id])
        self.app.handle_renamed_file(old_path, new_path)
        self.assertEqual(self.app.tab_filepaths[tab_id], new_path)
        self.app.notebook.tab.assert_called_once_with(tab_id, text='path.txt*')
        self.app.status_bar.update_filepath.assert_called()

    def test_handle_deleted_file(self):
        tab_id = '.!notebook.!frame'
        deleted_path = '/path/to/deleted_file.txt'
        self.app.tab_filepaths = {tab_id: deleted_path}
        self.app.editors = {tab_id: MagicMock(spec=TextEditor)}
        self.app.notebook.forget = MagicMock()
        self.app.handle_deleted_file(deleted_path)
        self.app.notebook.forget.assert_called_once_with(tab_id)
        self.assertNotIn(tab_id, self.app.editors)
        self.assertNotIn(tab_id, self.app.tab_filepaths)

    def test_toggle_search_frame_show_hide(self):
        self.app.search_frame_visible = False
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._toggle_search_frame()
            self.app.search_frame.pack.assert_called_once()
            self.assertTrue(self.app.search_frame_visible)
            self.app.search_entry.focus_set.assert_called_once()
            mock_editor.clear_search_highlights = MagicMock()
            self.app._toggle_search_frame()
            self.app.search_frame.pack_forget.assert_called_once()
            self.assertFalse(self.app.search_frame_visible)
            mock_editor.clear_search_highlights.assert_called_once()
            mock_editor.text_area.focus_set.assert_called_once()

    def test_find_next_found(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = '1.5'
        self.app.search_entry.get.return_value = 'test'
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._find_next()
        mock_editor.clear_search_highlights.assert_called_once()
        mock_editor.text_area.search.assert_called_once_with('test', '1.0',
            stopindex=tk.END, nocase=True)
        mock_editor.text_area.tag_add.assert_called_once_with(
            'search_highlight', '1.5', '1.5+4c')
        mock_editor.text_area.see.assert_called_once_with('1.5')
        mock_editor.text_area.mark_set.assert_called_once_with(tk.INSERT,
            '1.5+4c')
        self.assertEqual(self.app.last_search_match_info, {'index':
            '1.5+4c', 'query': 'test'})

    def test_find_next_not_found_then_wrap(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.side_effect = ['', '1.2']
        self.app.search_entry.get.return_value = 'wrap'
        self.app.last_search_match_info = {'index': '5.0', 'query': 'wrap'}
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._find_next()
        self.assertEqual(mock_editor.text_area.search.call_count, 2)
        mock_editor.text_area.search.assert_any_call('wrap', '5.0',
            stopindex=tk.END, nocase=True)
        mock_editor.text_area.search.assert_any_call('wrap', '1.0',
            stopindex='5.0', nocase=True)
        mock_editor.text_area.tag_add.assert_called_once_with(
            'search_highlight', '1.2', '1.2+4c')
        self.app.status_bar.update_status.assert_any_call(
            "'wrap' not found. Wrapping around.")

    def test_find_next_case_sensitive_match(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = '1.0'
        self.app.search_entry.get.return_value = 'Test'
        self.app.case_sensitive_var.set(True)
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._find_next()
        args, kwargs = mock_editor.text_area.search.call_args
        self.assertFalse(kwargs.get('nocase', True),
            'Search should have been case-sensitive (nocase=False)')
        mock_editor.text_area.tag_add.assert_called_once()
        self.app.status_bar.update_status.assert_called_with("Found: 'Test'")

    def test_find_next_case_insensitive_match_via_option(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = '1.0'
        self.app.search_entry.get.return_value = 'test'
        self.app.case_sensitive_var.set(False)
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._find_next()
        args, kwargs = mock_editor.text_area.search.call_args
        self.assertTrue(kwargs.get('nocase', False),
            'Search should have been case-insensitive (nocase=True)')
        self.app.status_bar.update_status.assert_called_with("Found: 'test'")

    def test_find_previous_case_sensitive_match(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.text_area = MagicMock()
        mock_editor.text_area.search.return_value = '1.0'
        self.app.search_entry.get.return_value = 'Test'
        self.app.case_sensitive_var.set(True)
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._find_previous()
        args, kwargs = mock_editor.text_area.search.call_args
        self.assertFalse(kwargs.get('nocase', True),
            'Search should have been case-sensitive (nocase=False)')
        self.assertTrue(kwargs.get('backwards'),
            'Search should have been backwards')
        self.app.status_bar.update_status.assert_called_with("Found: 'Test'")

    def test_on_search_option_changed_clears_last_match(self):
        mock_editor = MagicMock(spec=TextEditor)
        mock_editor.clear_search_highlights = MagicMock()
        self.app.last_search_match_info = {'index': '5.5', 'query': 'old_query'
            }
        self.app.search_entry.get.return_value = 'new_query'
        with patch.object(self.app, 'get_current_editor', return_value=
            mock_editor):
            self.app._on_search_option_changed()
        self.assertEqual(self.app.last_search_match_info, {'index': '1.0',
            'query': 'new_query'})
        mock_editor.clear_search_highlights.assert_called_once()


if __name__ == '__main__':
    unittest.main()
