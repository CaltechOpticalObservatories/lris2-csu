
from inputTargets import TargetList
from targetListWidget import TargetDisplayWidget
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QStackedLayout,
    QLineEdit,
    QFormLayout,
    QGroupBox,
    QBoxLayout
    
)



class MaskGenWidget(QWidget):
    change_data = pyqtSignal(list)
    def __init__(self):
        super().__init__()

        
        #self.setFixedSize(200,400)
        #self.setStyleSheet("border: 2px solid black;")
        import_target_list_button = QPushButton(text = "Import Target List")
        name_of_mask = QLineEdit()
        name_of_mask.setAlignment(Qt.AlignmentFlag.AlignTop)
        import_target_list_button.setFixedSize(150,40)

        group_box = QGroupBox()
        main_layout = QVBoxLayout()
        secondary_layout = QFormLayout()
        group_layout = QVBoxLayout()
        group_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        #group_box.setStyleSheet("border: 2px solid black;")

        

        import_target_list_button.clicked.connect(self.starlist_file_button_clicked)


        #layout.addWidget(main_widget)

        secondary_layout.addRow("Mask Name:",name_of_mask)
        group_layout.addLayout(secondary_layout)

        group_layout.addWidget(import_target_list_button)
        group_box.setLayout(group_layout)
        main_layout.addWidget(group_box)

        #xwidget.setLayout(layout)


        self.setLayout(main_layout)
        #self.show()
        

    def starlist_file_button_clicked(self):
        text_file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a File",
            "",
            "All files (*)" 
        )

        if text_file_path: 
            print(f"Selected file: {text_file_path}")
            target_list = TargetList(text_file_path)
            #self.new_data_list.emit(target_list.send_list())
            self.change_data.emit(target_list.send_list())
            
            #TargetDisplayWidget(target_list.send_list())


            

            