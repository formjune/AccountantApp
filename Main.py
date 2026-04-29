import sys
import os
try:
    from PyQt5.Qt import *
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
sys.path.append(os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from ui import MainWindow, Application


main_window = MainWindow.MainWindow()
main_window.showMaximized()
sys.exit(Application.app.exec())
