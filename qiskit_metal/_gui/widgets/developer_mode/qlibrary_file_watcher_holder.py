import os
import typing

from PySide2.QtGui import QFont
from PySide2.QtCore import QFileSystemWatcher, Qt, Signal, QModelIndex
from PySide2.QtWidgets import QFileSystemModel, QWidget

file_dirtied_signal = Signal()
file_cleaned_signal = Signal()


class QLibraryFileWatcherHolder():

    def __init__(self, qlibrary_path: str, parent: QWidget = None):
        """
        Initializes Model

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.file_system_watcher = QFileSystemWatcher()
        self.dirtied_files = {}
        self.ignored_substrings = {'.cpython', '__pycache__'}
        self.qlibrary_path = qlibrary_path
        self.set_root_path(self.qlibrary_path)

    def set_root_path(self, path: str):
        """
        Sets FileWatcher on root path
        Args:
            path: Root path

        """

        for root, _, files in os.walk(path):
            # do NOT use directory changed -- fails for some reason
            for name in files:
                self.file_system_watcher.addPath(os.path.join(root, name))

        self.file_system_watcher.fileChanged.connect(self.alert_highlight_row)



    def alert_highlight_row(self, filepath: str):
        """
        Dirties file and re-adds edited file to the FileWatcher
        Args:
            filepath: Dirty file


        """
        # ensure get only filename
        if filepath not in self.file_system_watcher.files():
            if os.path.exists(filepath):
                self.file_system_watcher.addPath(filepath)
        self.dirty_file(filepath)


    def is_file_dirty(self, filepath: str) -> bool:
        """
        Checks whether file is dirty
        Args:
            filepath: File in question

        Returns: Whether file is dirty

        """
        filename = self.filepath_to_filename(filepath)
        return filename in self.dirtied_files

    def dirty_file(self, filepath: str):
        """
        Adds file and parent directories to the dirtied_files dictionary.
        Emits file_dirtied_signal
        Args:
            filepath: Dirty file path

        """
        filename = self.filepath_to_filename(filepath)
        if not self.is_valid_file(filename):
            return

        sep = os.sep if os.sep in filepath else '/'
        for file in filepath.split(sep):

            if file in self.dirtied_files:
                self.dirtied_files[file].add(filename)
            else:
                self.dirtied_files[file] = {filename}

        # overwrite filename entry from above
        self.dirtied_files[filename] = {filepath}

        self.file_dirtied_signal.emit()


    def filepath_to_filename(self, filepath: str) -> str:  # pylint: disable=R0201, no-self-use
        """
        Gets just the filename from the full filepath
        Args:
            filepath: Full file path

        Returns: Filename

        """

        # split on os.sep and / because PySide appears to sometimes use / on
        # certain Windows
        filename = filepath.split(os.sep)[-1].split('/')[-1]
        if '.py' in filename:
            return filename[:-len('.py')]
        return filename


    def clean_file(self, filepath: str):
        """
        Remove file from the dirtied_files dictionary
        and remove any parent files who are only dirty due to
        this file. Emits file_cleaned_signal.
        Args:
            filepath: Clean file path

        """
        filename = self.filepath_to_filename(filepath)
        self.dirtied_files.pop(filename, f"failed to pop {filepath}")

        sep = os.sep if os.sep in filepath else '/'
        for file in filepath.split(sep):
            if file in self.dirtied_files:
                # if file was in dirtied files only because it is a parent dir
                # of filename, remove
                self.dirtied_files[file].discard(filename)

                if len(self.dirtied_files[file]) < 1:
                    self.dirtied_files.pop(file)
        self.file_cleaned_signal.emit()

    def is_valid_file(self, file: str):
        """
        Whether it's a file the FileWatcher should track
        Args:
            file: Filename

        Returns: Whether file is one the FileWatcher should track

        """
        for sub in self.ignored_substrings:
            if sub in file:
                return False
        return True