"""
This is a widget that will display all the masks that have been imported and if they have been saved.
A button at the bottom to save the mask, and one right next to it to save all the masks
3 buttons on the top: open, copy, close
"""

from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QGroupBox,
    QTableView,
)

class Button(QPushButton):
    def __init__(self,w,h,text):
        super().__init__()
        self.setText(text)
        self.setFixedSize(w,h)

class TableModel(QAbstractTableModel):
    def __init__(self, data=[]):
        super().__init__()
        self._data = data
    def headerData(self, section, orientation, role = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            #should add something about whether its vertical or horizontal
            if orientation == Qt.Orientation.Horizontal:
                return ["Status","Name"][section]
            if orientation == Qt.Orientation.Vertical:
                return None
        return super().headerData(section, orientation, role)

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self._data[0])


#I am unsure of whether to go with a abstract table model or an abstract list model
class MaskConfigurationsWidget(QWidget):
    def __init__(self):
        super().__init__()
        #self.setStyleSheet("border: 2px solid black;")

        temp_data = [["saved","batmask"],["unsaved","spidermask"]]

        open_button = Button(80,30,"Open")
        copy_button = Button(80,30,"Copy")
        close_button = Button(80,30,"Close")

        save_button = Button(120,30,"Save")
        save_all_button = Button(120,30,"Save All")

        group_box = QGroupBox("MASK CONFIGURATIONS")
        
        table = QTableView()
        model = TableModel(temp_data)
        table.setModel(model)
        table.setBaseSize(200,200)

        main_layout = QVBoxLayout()
        group_layout = QVBoxLayout()
        top_hori_layout = QHBoxLayout()
        bot_hori_layout = QHBoxLayout()

        top_hori_layout.addWidget(open_button)
        top_hori_layout.addWidget(copy_button)
        top_hori_layout.addWidget(close_button)

        bot_hori_layout.addWidget(save_button)
        bot_hori_layout.addWidget(save_all_button)

        group_layout.addLayout(top_hori_layout)
        group_layout.addWidget(table)
        group_layout.addLayout(bot_hori_layout)

        group_box.setLayout(group_layout)

        main_layout.addWidget(group_box)

        self.setLayout(main_layout)



