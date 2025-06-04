from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QPushButton, QLabel, QComboBox, QSpacerItem)


class MainViewWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        self.setWindowTitle(self.tr("PressureCalibration"))
        self.setMinimumSize(600, 400)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # 软件设置，pCan选择，波特率，等设置
        self.box_pcan_set = QGroupBox(self.tr("PCAN Setting"))
        self.layout.addWidget(self.box_pcan_set, 2)

        lay_pcan_set = QVBoxLayout()
        lay_pcan_set.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.box_pcan_set.setLayout(lay_pcan_set)

        # 软件设置，pCan扫描选择
        lay_pcan_scan = QHBoxLayout()
        lay_pcan_set.addLayout(lay_pcan_scan)
        lay_pcan_scan.addWidget(QLabel(self.tr("PCAN")), 1)

        self.combo_pacn_scan = QComboBox()
        lay_pcan_scan.addWidget(self.combo_pacn_scan, 6)

        btn_pcan_scan = QPushButton(self.tr("Refresh"))
        lay_pcan_scan.addWidget(btn_pcan_scan, 2)

        # 软件设置，波特率选择
        lay_pcan_baud = QHBoxLayout()
        lay_pcan_set.addLayout(lay_pcan_baud)

        lay_pcan_baud.addWidget(QLabel(self.tr("Baudrate")), 1)

        self.combo_pcan_baud = QComboBox()
        lay_pcan_baud.addWidget(self.combo_pcan_baud, 8)

        # 软件设置，初始化PCAN
        lay_pcan_init = QVBoxLayout()
        lay_pcan_set.addLayout(lay_pcan_init)

        self.btn_pcan_init = QPushButton(self.tr("Connect"))
        lay_pcan_init.addSpacerItem(QSpacerItem(0, 100))
        lay_pcan_init.addWidget(self.btn_pcan_init)

        # 压力传感器设置，修改ID，修改发送间隔时间，读取数据，修改标定参数
        self.box_sensor_set = QGroupBox(self.tr("Transducer Setting"))
        self.layout.addWidget(self.box_sensor_set, 8)
        # self.box_sensor_set.setEnabled(False)  # 禁用




