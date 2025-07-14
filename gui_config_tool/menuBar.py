

from PyQt6.QtGui import QAction
#from inputTargets import TargetList
from PyQt6.QtWidgets import QMenuBar

'''
menu bar will have a file option, and a help option for now
the file option will have import section and export section seperated by a line
'''

class MenuBar(QMenuBar):
    def __init__(self):
        super().__init__()
        import_button = QAction("&import",self)
        export_button = QAction("&export",self)
        help_button = QAction("&No Help",self)

        file_menu = self.addMenu("&File")
        file_menu.addAction(import_button)
        file_menu.addSeparator()
        file_menu.addAction(export_button)

        help_menu = self.addMenu("&Help")
        help_menu.addAction(help_button)

        