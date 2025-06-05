import os

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QPushButton, QLabel, QComboBox, QSpacerItem, QTableView,
                               QSpinBox, QMessageBox, QCheckBox, QLineEdit)

from .CustomWidget import CustomTableModel, CustomTableAcqButtonDelegate
from .dataModel import SensorCalParamList, SensorCalParam
from . import pCANBasic
from . import tool


class MainViewWindow(QMainWindow):
    max_spin_edit_id = 254
    max_spin_edit_freq = 500
    interval_freq_list = ["10ms", "20ms", "30ms", "40ms", "50ms",
                          "60ms", "70ms", "80ms", "90ms", "100ms",
                          "110ms", "120ms", "130ms", "140ms", "150ms",
                          "160ms", "170ms", "180ms", "190ms", "200ms"]

    pcan_baud_rate_list = {'1 MBit/sec': pCANBasic.PCAN_BAUD_1M, '800 kBit/sec': pCANBasic.PCAN_BAUD_800K,
                           '500 kBit/sec': pCANBasic.PCAN_BAUD_500K,
                           '250 kBit/sec': pCANBasic.PCAN_BAUD_250K,
                           '125 kBit/sec': pCANBasic.PCAN_BAUD_125K, '100 kBit/sec': pCANBasic.PCAN_BAUD_100K,
                           '95,238 kBit/sec': pCANBasic.PCAN_BAUD_95K, '83,333 kBit/sec': pCANBasic.PCAN_BAUD_83K,
                           '50 kBit/sec': pCANBasic.PCAN_BAUD_50K, '47,619 kBit/sec': pCANBasic.PCAN_BAUD_47K,
                           '33,333 kBit/sec': pCANBasic.PCAN_BAUD_33K, '20 kBit/sec': pCANBasic.PCAN_BAUD_20K,
                           '10 kBit/sec': pCANBasic.PCAN_BAUD_10K, '5 kBit/sec': pCANBasic.PCAN_BAUD_5K}

    def __init__(self):
        super().__init__()
        self.table_header_label = [self.tr("AD value"), self.tr("Physical value (10KPa)"), self.tr("Acq AD")]
        self.sensorCalParamList: SensorCalParamList = SensorCalParamList()
        self.drv = pCANBasic.PCANBasic()
        self.pcan_scan_list = []
        self.is_connect = False  # 是否连接
        self.is_admin = False  # 是否管理员权限
        self.is_broadcast = False  # 是否进行广播写入
        self.current_can_id = 0  # 当前的Can Id

        self.check_admin()
        print(self.is_admin)
        self.initUi()
        self.initSignalCallback()

    def initUi(self):
        self.setWindowTitle(self.tr("PressureCalibration"))
        self.setMinimumSize(700, 450)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # 软件设置，pCan选择，波特率，等设置
        self.box_pcan_set = QGroupBox(self.tr("PCAN Setting"))
        self.layout.addWidget(self.box_pcan_set, 3)

        # PCAN设置，参数保存
        lay_pcan_save_set = QVBoxLayout()
        self.box_pcan_set.setLayout(lay_pcan_save_set)

        # PCAN设置
        lay_pcan_set = QVBoxLayout()
        lay_pcan_set.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay_pcan_save_set.addLayout(lay_pcan_set, 5)

        # 软件设置，pCan扫描选择
        lay_pcan_scan = QHBoxLayout()
        lay_pcan_set.addLayout(lay_pcan_scan)
        lay_pcan_scan.addWidget(QLabel(self.tr("PCAN")), 1)

        self.combo_pacn_scan = QComboBox()
        lay_pcan_scan.addWidget(self.combo_pacn_scan, 6)

        self.btn_pcan_scan = QPushButton(self.tr("Refresh"))
        self.btn_pcan_scan.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #0078D7;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 14px;
        }
        ''')
        lay_pcan_scan.addWidget(self.btn_pcan_scan, 2)

        # 软件设置，波特率选择
        lay_pcan_baud = QHBoxLayout()
        lay_pcan_set.addLayout(lay_pcan_baud)

        lay_pcan_baud.addWidget(QLabel(self.tr("Baudrate")), 1)

        self.combo_pcan_baud = QComboBox()
        self.combo_pcan_baud.addItems(list(self.pcan_baud_rate_list.keys()))
        self.combo_pcan_baud.setCurrentIndex(11)
        lay_pcan_baud.addWidget(self.combo_pcan_baud, 8)

        # 软件设置，初始化PCAN
        lay_pcan_init = QVBoxLayout()
        lay_pcan_set.addLayout(lay_pcan_init)

        self.btn_pcan_init = QPushButton(self.tr("Connect"))
        lay_pcan_init.addSpacerItem(QSpacerItem(0, 50))
        lay_pcan_init.addWidget(self.btn_pcan_init)

        # 参数保存
        lay_save_set = QVBoxLayout()
        lay_pcan_save_set.addLayout(lay_save_set, 5)

        self.btn_cal_save = QPushButton(self.tr("Cal Write"))
        self.btn_plant_save = QPushButton(self.tr("Plant Save"))
        self.btn_recover_plant = QPushButton(self.tr("Recover Plant"))
        lay_save_set.addWidget(self.btn_cal_save)
        lay_save_set.addWidget(self.btn_plant_save)
        lay_save_set.addWidget(self.btn_recover_plant)
        if self.is_admin:
            self.check_btn_broadcast = QCheckBox(self.tr("Broadcast writing"))
            lay_save_set.addWidget(self.check_btn_broadcast)

        # 压力传感器设置，设置标定参数
        self.box_sensor_set = QGroupBox(self.tr("Sensor Setting"))
        self.layout.addWidget(self.box_sensor_set, 7)
        # self.box_sensor_set.setEnabled(False)  # 禁用

        lay_sensor_set = QVBoxLayout()
        self.box_sensor_set.setLayout(lay_sensor_set)

        # 设置标定参数
        box_sensor_cal = QGroupBox(self.tr("Calibration"))
        lay_sensor_set.addWidget(box_sensor_cal)

        lay_sensor_cal = QVBoxLayout()
        box_sensor_cal.setLayout(lay_sensor_cal)

        lay_btn_sensor_cal = QHBoxLayout()
        lay_sensor_cal.addLayout(lay_btn_sensor_cal)

        self.btn_sensor_cal_add = QPushButton(self.tr("Add"))
        self.btn_sensor_cal_minus = QPushButton(self.tr("Remove"))
        self.btn_sensor_cal_sort = QPushButton(self.tr("Sort"))
        self.btn_sensor_cal_sort.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #0078D7;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 14px;
        }
        ''')
        lay_btn_sensor_cal.addWidget(self.btn_sensor_cal_add, 2)
        lay_btn_sensor_cal.addWidget(self.btn_sensor_cal_minus, 2)
        lay_btn_sensor_cal.addWidget(self.btn_sensor_cal_sort, 1)

        self.table_view_sensor_cal = QTableView()
        lay_sensor_cal.addWidget(self.table_view_sensor_cal)
        # self.table_sensor_cal.verticalHeader().setHidden(True)

        self.table_model = CustomTableModel(self.table_header_label, self.sensorCalParamList)
        self.table_view_sensor_cal.setModel(self.table_model)

        self.table_btn_delegate_acq = CustomTableAcqButtonDelegate()
        self.table_view_sensor_cal.setItemDelegateForColumn(2, self.table_btn_delegate_acq)

        # 修改ID，修改发送间隔时间，读取数据，保存数据
        lay_sensor_edit = QHBoxLayout()
        lay_sensor_set.addLayout(lay_sensor_edit)

        # 修改ID，修改发送间隔时间，读取数据，
        lay_sensor_edit_ = QVBoxLayout()
        lay_sensor_edit.addLayout(lay_sensor_edit_)

        # 修改ID
        lay_edit_id = QHBoxLayout()
        lay_sensor_edit_.addLayout(lay_edit_id)
        lay_edit_id.addWidget(QLabel(self.tr("Can Id")), 2)

        self.spin_edit_id = QSpinBox()
        self.spin_edit_id.setMinimum(1)
        self.spin_edit_id.setMaximum(self.max_spin_edit_id)
        # self.spin_edit_id.setSuffix("    Dec")
        lay_edit_id.addWidget(self.spin_edit_id, 5)

        self.btn_read_id = QPushButton(self.tr("Read"))
        self.btn_read_id.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #ffa657;
            border: none;
            border-radius: 5px;
            padding: 3px 5px;
            font-size: 14px;
        }
        ''')
        self.btn_edit_id = QPushButton(self.tr("Write"))
        self.btn_edit_id.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #0078D7;
            border: none;
            border-radius: 5px;
            padding: 3px 5px;
            font-size: 14px;
        }
        ''')
        lay_edit_id.addWidget(self.btn_read_id, 1)
        lay_edit_id.addWidget(self.btn_edit_id, 1)

        # 修改发送间隔时间
        lay_edit_freq = QHBoxLayout()
        lay_sensor_edit_.addLayout(lay_edit_freq)
        lay_edit_freq.addWidget(QLabel(self.tr("Interval")), 2)

        # self.spin_edit_freq = QSpinBox()
        # self.spin_edit_freq.setMinimum(25)
        # self.spin_edit_freq.setMaximum(self.max_spin_edit_freq)
        # self.spin_edit_freq.setSuffix("    ms")
        # lay_edit_freq.addWidget(self.spin_edit_freq, 5)
        self.combo_edit_freq = QComboBox()
        self.combo_edit_freq.addItems(self.interval_freq_list)
        lay_edit_freq.addWidget(self.combo_edit_freq, 5)

        self.btn_read_freq = QPushButton(self.tr("Read"))
        self.btn_read_freq.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #ffa657;
            border: none;
            border-radius: 5px;
            padding: 3px 5px;
            font-size: 14px;
        }
        ''')
        self.btn_edit_freq = QPushButton(self.tr("Write"))
        self.btn_edit_freq.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #0078D7;
            border: none;
            border-radius: 5px;
            padding: 3px 5px;
            font-size: 14px;
        }
        ''')
        lay_edit_freq.addWidget(self.btn_read_freq, 1)
        lay_edit_freq.addWidget(self.btn_edit_freq, 1)

        # 修改传感器SN
        if self.is_admin:
            lay_edit_sn = QHBoxLayout()
            lay_sensor_edit_.addLayout(lay_edit_sn)
            lay_edit_sn.addWidget(QLabel(self.tr("SN")), 2)
            self.input_edit_sn = QLineEdit()
            lay_edit_sn.addWidget(self.input_edit_sn, 5)
            self.btn_read_sn = QPushButton(self.tr("Read"))
            self.btn_read_sn.setStyleSheet('''
            QPushButton {
                color: white;
                background-color: #ffa657;
                border: none;
                border-radius: 5px;
                padding: 3px 5px;
                font-size: 14px;
            }
            ''')
            self.btn_edit_sn = QPushButton(self.tr("Write"))
            self.btn_edit_sn.setStyleSheet('''
            QPushButton {
                color: white;
                background-color: #0078D7;
                border: none;
                border-radius: 5px;
                padding: 3px 5px;
                font-size: 14px;
            }
            ''')

            lay_edit_sn.addWidget(self.btn_read_sn, 1)
            lay_edit_sn.addWidget(self.btn_edit_sn, 1)

        # 读取数据，
        lay_read_data = QHBoxLayout()
        lay_sensor_edit_.addLayout(lay_read_data)

        # ad值
        lay_read_sensor_ad = QVBoxLayout()
        lay_read_data.addLayout(lay_read_sensor_ad)

        label_read_ad_value = QLabel(self.tr("AD Value"))
        label_read_ad_value.setStyleSheet('''
        QLabel {
            color: #ff8936;
            font-size: 16px;
            font-weight: bold;
        }
        ''')
        lay_read_sensor_ad.addWidget(label_read_ad_value)

        self.text_read_ad_value = QLabel("00000")
        self.text_read_ad_value.setStyleSheet('''
        QLabel {
            color: white;
            font-size: 22px;
            font-weight: 400;
            background-color: #3A3A3A;
            border: 2px solid #555;
            border-radius: 6px;
            padding: 12px;
            margin: 5px;
        }
        ''')
        self.text_read_ad_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay_read_sensor_ad.addWidget(self.text_read_ad_value)

        # 物理值
        lay_read_sensor_val = QVBoxLayout()
        lay_read_data.addLayout(lay_read_sensor_val)

        label_read_sensor_value = QLabel(self.tr("Pressure Value (10KPa)"))
        label_read_sensor_value.setStyleSheet('''
        QLabel {
            color: #02913a;
            font-size: 16px;
            font-weight: bold;
        }
        ''')
        lay_read_sensor_val.addWidget(label_read_sensor_value)

        self.text_read_sensor_value = QLabel("00000")
        self.text_read_sensor_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.text_read_sensor_value.setStyleSheet('''
        QLabel {
            color: white;
            font-size: 22px;
            font-weight: 400;
            background-color: #3A3A3A;
            border: 2px solid #555;
            border-radius: 6px;
            padding: 12px;
            margin: 5px;
        }
        ''')

        lay_read_sensor_val.addWidget(self.text_read_sensor_value)

    def initSignalCallback(self):
        self.btn_pcan_scan.clicked.connect(self.on_pcan_scan_btn_click)
        self.btn_pcan_init.clicked.connect(self.on_pcan_init_btn_click)
        self.btn_sensor_cal_add.clicked.connect(self.on_sensor_cal_add_btn_click)
        self.btn_sensor_cal_minus.clicked.connect(self.on_sensor_cal_minus_btn_click)
        self.btn_sensor_cal_sort.clicked.connect(self.on_sensor_cal_sort_btn_click)
        self.btn_edit_id.clicked.connect(self.on_edit_id_btn_click)
        self.btn_read_id.clicked.connect(self.on_read_id_btn_click)
        self.btn_edit_freq.clicked.connect(self.on_edit_freq_btn_click)
        self.btn_read_freq.clicked.connect(self.on_read_freq_btn_click)
        self.btn_cal_save.clicked.connect(self.on_cal_save_btn_click)
        self.btn_plant_save.clicked.connect(self.on_plant_save_btn_click)
        self.btn_recover_plant.clicked.connect(self.on_recover_plant_btn_click)
        self.table_btn_delegate_acq.clicked.connect(self.on_table_acq_btn_click)

        if self.is_admin:
            self.check_btn_broadcast.checkStateChanged.connect(
                lambda state, obj=self: setattr(obj, 'is_broadcast', state == Qt.CheckState.Checked)
            )
            self.btn_edit_sn.clicked.connect(self.on_edit_sn_btn_click)
            self.btn_read_sn.clicked.connect(self.on_read_sn_btn_click)

    def on_pcan_scan_btn_click(self):
        self.pcan_scan_list.clear()
        items = []
        self.combo_pacn_scan.clear()
        result = self.drv.GetValue(pCANBasic.PCAN_NONEBUS, pCANBasic.PCAN_ATTACHED_CHANNELS)
        if result[0] != pCANBasic.PCAN_ERROR_OK:
            pass
        for channel in result[1]:
            if channel.channel_condition & channel.PCAN_CHANNEL_AVAILABLE:
                items.append(self.FormatChannelName(channel.channel_handle,
                                                    channel.device_features & pCANBasic.FEATURE_FD_CAPABLE))

        self.combo_pacn_scan.addItems(items)

    def on_pcan_init_btn_click(self):
        if self.combo_pacn_scan.count() == 0:
            QMessageBox.critical(self, self.tr("Error"), self.tr("The PCAN hardware was not found"))
            return

    def on_sensor_cal_add_btn_click(self):
        if len(self.sensorCalParamList.sensorCalParam) == 0:
            self.sensorCalParamList.sensorCalParam.append(SensorCalParam())
        else:
            self.sensorCalParamList.sensorCalParam.append(
                SensorCalParam(
                    adValue=self.sensorCalParamList.sensorCalParam[-1].adValue + 10,
                    rangeValue=self.sensorCalParamList.sensorCalParam[-1].rangeValue + 10
                )
            )
        self.table_model.update()

    def on_sensor_cal_minus_btn_click(self):
        row = self.table_view_sensor_cal.currentIndex().row()
        if row >= 0:
            self.table_model.removeRow(row)

    def on_sensor_cal_sort_btn_click(self):
        self.sensorCalParamList.sort()
        self.table_model.update()

    def on_edit_id_btn_click(self):
        if not self.is_connect:
            return


        canMsg = pCANBasic.TPCANMsg()
        # canMsg.ID = self.

        pass

    def on_read_id_btn_click(self):
        pass

    def on_edit_freq_btn_click(self):
        pass

    def on_read_freq_btn_click(self):
        pass

    def on_edit_sn_btn_click(self):
        pass

    def on_read_sn_btn_click(self):
        pass

    def on_cal_save_btn_click(self):
        pass

    def on_plant_save_btn_click(self):
        pass

    def on_recover_plant_btn_click(self):
        pass

    def on_table_acq_btn_click(self, index: QModelIndex):
        self.sensorCalParamList.sensorCalParam[index.row()].adValue = 100
        self.table_model.update()

    def GetDeviceName(self, handle):
        switcher = {
            pCANBasic.PCAN_NONEBUS.value: "PCAN_NONEBUS",
            pCANBasic.PCAN_PEAKCAN.value: "PCAN_PEAKCAN",
            pCANBasic.PCAN_ISA.value: "PCAN_ISA",
            pCANBasic.PCAN_DNG.value: "PCAN_DNG",
            pCANBasic.PCAN_PCI.value: "PCAN_PCI",
            pCANBasic.PCAN_USB.value: "PCAN_USB",
            pCANBasic.PCAN_PCC.value: "PCAN_PCC",
            pCANBasic.PCAN_VIRTUAL.value: "PCAN_VIRTUAL",
            pCANBasic.PCAN_LAN.value: "PCAN_LAN"
        }

        return switcher.get(handle, "UNKNOWN")

    def FormatChannelName(self, handle, isFD=False):
        if handle < 0x100:
            devDevice = pCANBasic.TPCANDevice(handle >> 4)
            byChannel = handle & 0xF
        else:
            devDevice = pCANBasic.TPCANDevice(handle >> 8)
            byChannel = handle & 0xFF

        if isFD:
            toRet = ('%s: FD %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handle))
        else:
            toRet = ('%s: %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handle))

        return toRet

    def check_admin(self):
        path = os.path.join(os.getcwd(), ".admin")
        if not os.path.isfile(path):
            self.is_admin = False
            return

        self.is_admin = True
