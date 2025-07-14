"""
The GUI is in its very early stages. Its current features are the ability to take in a starlist file
and then display that file in a list
and a menu that doesn't do anything. 7/9/25
"""
"""
random stuff
GUI has to be able to send a command with the target lists to the mask back end
to call the slit mask algorithm with the code from the backend

the back end kind of already parses through a file that sorts all of the objects so I will
just take that and display that instead of through my awful input targets function 
(they also have a function to view the list)
"""


#just importing everything for now. When on the final stages I will not import what I don't need
from targetListWidget import TargetDisplayWidget
from importTargetListandRun import MaskGenWidget
from menuBar import MenuBar
from maskConfigurations import MaskConfigurationsWidget
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
)

class TempWidgets(QLabel):
    def __init__(self,w,h,text:str="hello"):
        super().__init__()
        self.setFixedSize(w,h)
        self.setText(text)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet("border: 2px solid black;")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LRIS-2 Slit Configuration Tool")
        self.setGeometry(100,100,1000,700)
        self.setMenuBar(MenuBar()) #sets the menu bar

        main_layout = QHBoxLayout()
        layoutH1 = QHBoxLayout()
        layoutV1 = QVBoxLayout() #left side
        layoutV2 = QVBoxLayout() #right side

        mask_config_widget = MaskConfigurationsWidget()
        mask_config_widget.setMaximumHeight(200)
        import_target_list_display = MaskGenWidget()
        sample_data = [[0,1,1,1],[1,0,1,1]]

        target_display = TargetDisplayWidget(sample_data)

        #temp_widget1 = TempWidgets(250,300,"Mask Configurations\nWill display a list of\nall previous configurations")
        temp_widget2 = TempWidgets(200,500,"This will display\nall of the widths\nand positions of\nthe bar pairs")
        temp_widget3 = TempWidgets(500,500,"This will display the current Mask Configuration")


        import_target_list_display.change_data.connect(target_display.change_data)

        layoutV2.addWidget(mask_config_widget)#temp_widget1
        layoutV2.addWidget(import_target_list_display)

        layoutH1.addWidget(temp_widget2)
        layoutH1.addWidget(temp_widget3)
        
        layoutV1.addLayout(layoutH1)
        layoutV1.addWidget(target_display)

        main_layout.addLayout(layoutV1)
        main_layout.addLayout(layoutV2)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)


app = QApplication([])
window = MainWindow()
window.show()
app.exec()