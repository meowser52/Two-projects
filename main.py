import sys
from main_window import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

app = QApplication(sys.argv)
app.setApplicationName("learn to write")
app.setWindowIcon(QIcon('images/texteditor.png'))
window = MainWindow()
window.show()
sys.exit(app.exec_())
