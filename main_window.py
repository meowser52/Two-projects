import json
import random
import time
import traceback
from pathlib import Path

import matplotlib.pyplot as plt
import qdarktheme
import wikipedia
from PyQt5.QtCore import (QSize, QFile, QTextStream, Qt)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtPrintSupport import QPrintDialog
from PyQt5.QtWidgets import (QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QToolBar,
                             QStatusBar, QWidget, QLineEdit, QPushButton, QDialogButtonBox, QGridLayout, QLayout)
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from utility import *


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.training_active = False
        self.sample_text = ''
        self.correct_input = ""

        # Open configuration file
        config_file = open('settings.json')
        config = json.load(config_file)

        self.error_history = 0
        # Set theme
        if config['use_default_theme'] == True:
            self.toggle_theme_default(config['theme'])
        else:
            self.toggle_theme_custom(config['stylesheet'])

        # Setup the QTextEdit editor configuration
        layout = QVBoxLayout()
        self.editor = QPlainTextEdit()

        # Setup default font
        font = QFont(config['default_font']['font_name'], config['default_font']['size'])
        self.editor.setFont(font)

        # Path of the currently open file
        self.path = None
        layout.addWidget(self.editor)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.statistics_file = "training_statistics.json"
        self.load_statistics()

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.error_label = QLabel()
        self.status.addPermanentWidget(self.error_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_word_count)
        self.timer.start(5000)

        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(14, 14))
        self.addToolBar(file_toolbar)
        file_menu = self.menuBar().addMenu("&File")

        set_open_file_action(file_menu, file_toolbar, config['shortcuts']['open'], self)
        set_save_file_action(file_menu, file_toolbar, config['shortcuts']['save'], self)
        set_saveas_file_action(file_menu, file_toolbar, self)
        set_print_action(file_menu, file_toolbar, config['shortcuts']['print'], self)

        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(edit_toolbar)
        edit_menu = self.menuBar().addMenu("&Edit")

        set_undo_action(edit_menu, edit_toolbar, self)
        set_redo_action(edit_menu, edit_toolbar, self)

        edit_menu.addSeparator()

        self.current_errors = 0
        set_cut_action(edit_toolbar, edit_menu, self)
        set_copy_action(edit_toolbar, edit_menu, self)
        set_paste_action(edit_toolbar, edit_menu, self)
        set_select_action(edit_menu, self)
        set_wrap_action(edit_menu, self)
        set_find_action(edit_menu, config['shortcuts']['find'], self)
        set_start_training_action(edit_toolbar, self)
        set_stop_training_action(edit_toolbar, self)
        set_wiki_start_training_action(edit_toolbar, self)
        set_show_statistics_action(edit_toolbar, self)
        set_clear_statistics_action(edit_toolbar, self)

        view_menu = self.menuBar().addMenu("&View")
        word_count_action = QAction("Word Count", self)
        word_count_action.triggered.connect(self.update_word_count)
        view_menu.addAction(word_count_action)

        self.editor.textChanged.connect(self.update_word_count)

        self.training_label = QLabel("")
        layout.addWidget(self.training_label)

        self.update_title()
        self.show()
        config_file.close()

    def load_statistics(self):
        if Path(self.statistics_file).is_file():
            with open(self.statistics_file, 'r') as file:
                try:
                    self.statistics = json.load(file)
                except json.JSONDecodeError:
                    self.statistics = []
        else:
            self.statistics = []

    def save_statistics(self):
        with open(self.statistics_file, 'w') as file:
            json.dump(self.statistics, file, indent=4)

    def update_statistics(self, completed, words_typed, elapsed_time, error_count):
        self.statistics.append({"completed": completed, "words_typed": words_typed, "elapsed_time": elapsed_time,
                                "error_count": error_count, "timestamp": time.time()})
        self.save_statistics()

    def show_statistics(self):
        self.load_statistics()

        if not self.statistics:
            QMessageBox.information(self, "Statistics", "No statistics available yet.")
            return

        total_sessions = len(self.statistics)
        words_per_session = [session['words_typed'] for session in self.statistics]
        time_per_session = [session['elapsed_time'] for session in self.statistics]
        errors_per_session = [session['error_count'] for session in self.statistics]

        dialog = QDialog(self)
        dialog.setWindowTitle("Training Statistics")
        layout = QVBoxLayout()

        figure = plt.figure()
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        sessions = range(1, total_sessions + 1)

        ax.plot(sessions, words_per_session, label='Words Typed')
        ax.plot(sessions, time_per_session, label='Time Elapsed (sec)')
        ax.plot(sessions, errors_per_session, label='Errors Made')
        ax.set_xlabel('Session Number')
        ax.set_title('Training Statistics')
        ax.legend()

        layout.addWidget(canvas)
        dialog.setLayout(layout)

        total_words_typed = sum(session['words_typed'] for session in self.statistics)
        total_time_elapsed = sum(session['elapsed_time'] for session in self.statistics)
        total_errors_made = sum(session['error_count'] for session in self.statistics)
        completed_sessions = sum(1 for session in self.statistics if session['completed'])

        summary_text = (f"Total sessions: {total_sessions}\n"
                        f"Completed sessions: {completed_sessions}\n"
                        f"Total words typed: {total_words_typed}\n"
                        f"Total time elapsed: {total_time_elapsed} seconds\n"
                        f"Total errors made: {total_errors_made}")

        summary_label = QLabel(summary_text)

        layout.addWidget(canvas)
        layout.addWidget(summary_label)
        dialog.setLayout(layout)

        dialog.exec_()

    def clear_statistics(self):
        reply = QMessageBox.question(self, 'Confirm Action', "Are you sure you want to clear all statistics?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            with open("training_statistics.json", "w") as file:
                file.write("[]")
            self.statistics = []
            QMessageBox.information(self, "Statistics", "Statistics cleared successfully.")

    def reset_training(self):
        original_text = self.sample_text
        self.editor.blockSignals(True)

        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.Document)
        format_reset = QTextCharFormat()
        format_reset.setBackground(QBrush(Qt.transparent))
        cursor.mergeCharFormat(format_reset)
        cursor.clearSelection()

        self.editor.clear()
        self.training_label.clear()

        self.editor.setPlainText(original_text)

        self.editor.blockSignals(False)

        try:
            self.editor.textChanged.disconnect(self.track_input)
        except TypeError:
            pass

    def stop_training(self, completed=False):
        if not self.training_active:
            QMessageBox.warning(self, "Training Not Started", "Start training before stopping it.")
            return

        elapsed_time = int(time.time() - self.start_time)
        elapsed_minutes = elapsed_time // 60
        elapsed_seconds = elapsed_time % 60
        words_typed = len(self.editor.toPlainText().split())
        words_per_minute = (words_typed / elapsed_time) * 60 if elapsed_time > 0 else 0

        self.training_active = False
        self.reset_training()

        self.update_statistics(completed, words_typed, elapsed_time, self.error_count)

        if completed:
            QMessageBox.information(self, "Training Completed", f"You have successfully completed the training!\n"
                                                                f"Words: {words_typed}, Time: {elapsed_minutes} min. {elapsed_seconds} sec., \n"
                                                                f"Words per minute: {words_per_minute:.2f}\n"
                                                                f"Errors: {self.error_count}")
        else:
            QMessageBox.information(self, "Training Stopped", f"The training has been stopped.\n"
                                                              f"Words: {words_typed}, Time: {elapsed_minutes} min. {elapsed_seconds} sec., \n"
                                                              f"Words per minute: {words_per_minute:.2f}\n"
                                                              f"Errors: {self.error_count}")

        self.update_word_count()

    def update_word_count(self):
        if self.training_active and hasattr(self, 'sample_text') and self.sample_text:
            words_left = len(self.sample_text.split()) - len(self.editor.toPlainText().split())
            elapsed_time = int(time.time() - self.start_time)
            elapsed_minutes = elapsed_time // 60
            elapsed_seconds = elapsed_time % 60
            self.error_label.setText(f"<span style='color:red;'>Errors: {self.error_count}</span>")
            self.status.showMessage(f"Words left: {words_left} | Time: {elapsed_minutes}:{elapsed_seconds:02d}")
        else:
            current_word_count = len(self.editor.toPlainText().split())
            self.status.showMessage(f"Word Count: {current_word_count}")
            self.error_label.clear()

    def update_training_label(self, user_input, max_words_per_line=10):
        html_text = "<pre>"
        word_count = 0
        for i, char in enumerate(self.sample_text):
            if char == ' ':
                word_count += 1
                if word_count >= max_words_per_line:
                    html_text += '<br>'
                    word_count = 0

            if i >= len(user_input):
                if i == len(user_input):
                    color = "background-color: rgba(255, 255, 0, 0.5);"
                else:
                    color = "background-color: rgba(128, 128, 128, 0.3);" if char == ' ' else ""

                char_html = char.replace(' ', '&nbsp;').replace('\n', '<br>')
                html_text += f"<span style='{color}'>{char_html}</span>"
            elif user_input[i] == char:
                span_char = char.replace(' ', '&nbsp;').replace('\n', '<br>')
                html_text += f"<span style='background-color: green;'>{span_char}</span>"
            else:
                span_char = char.replace(' ', '&nbsp;').replace('\n', '<br>')
                html_text += f"<span style='background-color: red;'>{span_char}</span>"
        html_text += "</pre>"
        self.training_label.setText(html_text)

    def start_training(self):
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Error", "Enter text for training before starting.")
            return
        elif len(text) > 1500:
            QMessageBox.warning(self, "Too Many Characters", "The training text is too long. Enter fewer characters.")
            return

        self.sample_text = text
        self.editor.clear()
        self.update_training_label("")
        self.start_time = time.time()
        self.error_count = 0
        self.editor.textChanged.connect(self.track_input)
        self.training_active = True
        self.update_word_count()

    def track_input(self):

        user_input = self.editor.toPlainText()
        self.update_training_label(user_input)

        new_errors = 0

        for i, (user_char, correct_char) in enumerate(zip(user_input, self.sample_text)):
            if user_char != correct_char:
                new_errors += 1

        if new_errors > self.current_errors:
            self.error_count += new_errors - self.current_errors

        self.current_errors = new_errors

        self.update_training_label(user_input)

        if user_input == self.sample_text:
            self.stop_training(completed=True)
            return

        user_input = self.editor.toPlainText()
        self.update_training_label(user_input)
        format_correct = QTextCharFormat()
        format_correct.setBackground(QBrush(QColor("green")))
        format_incorrect = QTextCharFormat()
        format_incorrect.setBackground(QBrush(QColor("red")))

        cursor = self.editor.textCursor()
        self.editor.blockSignals(True)

        cursor.setPosition(0)

        for i, char in enumerate(user_input):
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            if i < len(self.sample_text) and char == self.sample_text[i]:
                cursor.mergeCharFormat(format_correct)
            else:
                cursor.mergeCharFormat(format_incorrect)
            cursor.clearSelection()

        cursor.setPosition(len(user_input))
        self.editor.setTextCursor(cursor)
        self.editor.blockSignals(False)

    def get_wiki_text(self, max_length, lang='en'):
        assert isinstance(lang, str), "lang must be a string"
        wikipedia.set_lang(lang)

        featured_articles = wikipedia.page("Wikipedia:Featured articles").links

        while True:
            article_title = random.choice(featured_articles)
            print(f"Selected article title: {article_title} (type: {type(article_title)})")
            try:
                page = wikipedia.page(article_title)
                text = page.summary

                if len(text.split()) <= max_length:
                    return text, page.url
            except wikipedia.exceptions.DisambiguationError as e:
                continue
            except wikipedia.exceptions.PageError as e:
                continue

    def start_wiki_training(self):
        try:
            max_length = 200
            text, url = self.get_wiki_text(max_length)
            self.editor.setPlainText(text)
            self.status.showMessage(f"Loaded text from: {url}")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to load text from Wikipedia: {e}")

    def show_error(self, s):
        errorDialog = QMessageBox(self)
        errorDialog.addButton("Cancel", QMessageBox.ActionRole)

        errorDialog.setWindowTitle("Find")
        errorDialog.setText("Not Found {:s}.".format(s))
        errorDialog.setIcon(QMessageBox.Critical)
        errorDialog.exec_()

    def toggle_theme_default(self, theme):
        try:
            if theme == 'dark':
                app = QApplication.instance()
                app.setStyleSheet(qdarktheme.load_stylesheet(theme))
        except Exception as e:
            self.show_error(self, e)

    def toggle_theme_custom(self, path):
        try:
            app = QApplication.instance()
            file = QFile(path)
            file.open(QFile.ReadOnly | QFile.Text)
            stream = QTextStream(file)
            app.setStyleSheet(stream.readAll())
        except Exception as e:
            self.show_error(e)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "Text documents (*.txt);All files (*.*)")

        if path:
            try:
                with open(path, 'rU') as f:
                    text = f.read()

            except Exception as e:
                self.show_error(str(e))

            else:
                self.path = path
                self.editor.setPlainText(text)
                self.update_title()

    def save_file(self):
        if self.path is None:
            # If we do not have a path, we need to use Save As.
            return self.saveas_file()

        self._save_to_path(self.path)

    def saveas_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "Text documents (*.txt);All files (*.*)")

        if not path:
            # If dialog is cancelled, will return ''
            return

        self._save_to_path(path)

    def _save_to_path(self, path):
        text = self.editor.toPlainText()
        try:
            with open(path, 'w') as f:
                f.write(text)

        except Exception as e:
            self.show_error(str(e))

        else:
            self.path = path
            self.update_title()

    def print_file(self):
        dlg = QPrintDialog()
        if dlg.exec_():
            self.editor.print_(dlg.printer())

    def update_title(self):
        self.setWindowTitle("{:s} - learn to write".format(os.path.basename(self.path) if self.path else "Untitled"))

    def edit_toggle_wrap(self):
        self.editor.setLineWrapMode(1 if self.editor.lineWrapMode() == 0 else 0)

    def Find_word(self):
        self.findDialog = QDialog(self)

        findLabel = QLabel("Find Word:")
        self.lineEdit = QLineEdit()
        self.lineEdit.setText("")
        findLabel.setBuddy(self.lineEdit)

        replaceLabel = QLabel("Replace Word:")
        self.lineReplace = QLineEdit()
        self.lineReplace.setText("")
        replaceLabel.setBuddy(self.lineReplace)

        self.findButton = QPushButton("Find Next")
        self.findButton.setDefault(True)
        self.findButton.clicked.connect(self.searchText)

        self.replaceButton = QPushButton("Replace Next")
        self.replaceButton.setDefault(False)
        self.replaceButton.clicked.connect(self.replaceText)

        buttonBox = QDialogButtonBox(Qt.Vertical)
        buttonBox.addButton(self.findButton, QDialogButtonBox.ActionRole)
        buttonBox.addButton(self.replaceButton, QDialogButtonBox.ActionRole)

        topLeftLayout = QVBoxLayout()
        topLeftLayout.addWidget(findLabel)
        topLeftLayout.addWidget(self.lineEdit)
        topLeftLayout.addWidget(replaceLabel)
        topLeftLayout.addWidget(self.lineReplace)

        leftLayout = QVBoxLayout()
        leftLayout.addLayout(topLeftLayout)

        mainLayout = QGridLayout()
        mainLayout.setSizeConstraint(QLayout.SetFixedSize)
        mainLayout.addLayout(leftLayout, 0, 0)
        mainLayout.addWidget(buttonBox, 0, 1)
        mainLayout.setRowStretch(2, 1)
        self.findDialog.setLayout(mainLayout)

        self.findDialog.setWindowTitle("Find")
        self.findDialog.show()

    def searchText(self, replace=False):
        cursor = self.editor.textCursor()
        findIndex = cursor.anchor()
        text = self.lineEdit.text()
        content = self.editor.toPlainText()
        length = len(text)
        index = content.find(text, findIndex)

        if -1 == index:
            self.show_error("Not Found {:s}.".format(text))
        else:
            start = index

            cursor = self.editor.textCursor()
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, start + length)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, length)
            cursor.selectedText()
            if replace:
                cursor.insertText(self.lineReplace.text())
            self.editor.setTextCursor(cursor)

    def replaceText(self):
        self.searchText(True)
