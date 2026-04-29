import sys
try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
from ui import JsonWidget


app = QApplication(sys.argv)
widget = JsonWidget.Widget()
widget.show()
sys.exit(app.exec())
