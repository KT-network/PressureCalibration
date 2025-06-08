import os
import sys

from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from src.app import MainViewWindow

if __name__ == '__main__':
    try:
        app = QApplication([])

        locale = QLocale.system().name()
        translator = QTranslator()
        if translator.load(f"{os.getcwd()}\\translations\\{locale}.qm"):
            app.installTranslator(translator)

        app.setStyle('Fusion')
        screen = MainViewWindow()
        screen.show()


        sys.exit(app.exec())
    except IOError as e:
        print(e)