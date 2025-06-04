import sys

from PySide6.QtWidgets import QApplication

from src.app import MainViewWindow

if __name__ == '__main__':
    try:
        app = QApplication([])
        # app = ExceptionsCatch(sys.argv)
        app.setStyle('Fusion')
        screen = MainViewWindow()
        screen.show()

        # s = DebugWidget()
        # s.show()

        sys.exit(app.exec())
    except IOError as e:
        print(e)