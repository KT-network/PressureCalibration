import bisect
import json
import os

from PySide6.QtCore import Qt, QModelIndex, QThread, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QPushButton, QLabel, QComboBox, QSpacerItem, QTableView,
                               QSpinBox, QMessageBox, QCheckBox, QLineEdit, QProgressBar, QFileDialog)
from enum import IntEnum

from .CustomWidget import CustomTableModel, CustomTableAcqButtonDelegate
from .dataModel import SensorCalParamList, SensorCalParam
from . import pCANBasic
from . import tool
from .work import ReadCanMsgWork


class Command(IntEnum):
    ID = 0x02
    Freq = 0x1E
    Save = 0x1D
    Reset = 0xD3
    Switch = 0xE0  # 自定义指令，切换功能（0上报物理值，1上报ad值，2进行校准数据保存）
    Cal = 0xE1


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
    broadcast_id = 0xFF

    def __init__(self):
        super().__init__()
        self.table_header_label = [self.tr("AD value"), self.tr("Physical value (10KPa)"), self.tr("Acq AD")]
        self.sensorCalParamList: SensorCalParamList = SensorCalParamList()
        self.drv = pCANBasic.PCANBasic()
        self.pCanHandle = pCANBasic.PCAN_NONEBUS
        self.workThread = None
        self.worker = None

        self.pcan_scan_list = []
        self.is_connect = False  # 是否连接
        self.is_admin = False  # 是否管理员权限
        self.is_broadcast = False  # 是否进行广播写入
        self.is_scan_can_id = False  # 是否点击了扫描canId按钮
        self.scan_can_id_list = []  # 扫描到的canId列表
        self.current_can_id = -1  # 当前的Can Id
        self.current_sensor_ad_value = 0

        self.check_admin()
        self.initUi()
        self.initSignalCallback()
        self.set_enable(False)

    def initUi(self):
        self.setWindowTitle(self.tr("PressureCalibration"))
        self.setMinimumSize(700, 450)
        self.setWindowIcon(QIcon(f'{os.getcwd()}\\logo.ico'))

        self.status_bar_progress = QProgressBar()
        self.status_bar_progress.setMinimum(0)
        self.status_bar_progress.setMaximum(100)
        self.status_bar_progress.setValue(30)
        self.status_bar_progress.setMaximumHeight(15)
        self.status_bar_progress.setMaximumWidth(150)

        self.status_bar_progress.setStyleSheet("""
        QProgressBar {
            border: 1px solid;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #02913a;
            width: 50px;
        }
        """)
        self.status_bar_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_bar_label)
        self.statusBar().addPermanentWidget(self.status_bar_progress)
        self.status_bar_progress.hide()
        self.status_bar_label.hide()

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
        self.btn_pcan_init.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #0078D7;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 14px;
        }
        ''')

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
        self.btn_load_cal = QPushButton(self.tr("Load"))
        self.btn_save_cal = QPushButton(self.tr("Save"))

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
        lay_btn_sensor_cal.addWidget(self.btn_load_cal,1)
        lay_btn_sensor_cal.addWidget(self.btn_save_cal,1)

        lay_btn_sensor_cal.addWidget(self.btn_sensor_cal_sort, 1)

        self.table_view_sensor_cal = QTableView()
        lay_sensor_cal.addWidget(self.table_view_sensor_cal)
        # self.table_sensor_cal.verticalHeader().setHidden(True)
        # self.table_view_sensor_cal.verticalHeader().setFixedHeight(35)

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

        self.combo_edit_id = QComboBox()
        self.btn_edit_id_scan = QPushButton(self.tr("Scan"))
        self.btn_edit_id_scan.setStyleSheet('''
        QPushButton {
            color: white;
            background-color: #ffa657;
            border: none;
            border-radius: 5px;
            padding: 3px 5px;
            font-size: 14px;
        }
        ''')

        self.spin_edit_id = QSpinBox()
        self.spin_edit_id.setMinimum(1)
        self.spin_edit_id.setMaximum(self.max_spin_edit_id)
        # self.spin_edit_id.setSuffix("    Dec")
        lay_edit_id.addWidget(self.combo_edit_id, 2)
        lay_edit_id.addWidget(self.btn_edit_id_scan, 1)
        lay_edit_id.addWidget(self.spin_edit_id, 2)

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
        # lay_edit_id.addWidget(self.btn_read_id, 1)
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
        # lay_edit_freq.addWidget(self.btn_read_freq, 1)
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
        lay_read_sensor_ad.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay_read_sensor_ad.addSpacerItem(QSpacerItem(0, 10))

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
        # lay_read_sensor_ad.addSpacerItem(QSpacerItem(0,25))

        # 物理值
        lay_read_sensor_val = QVBoxLayout()
        lay_read_sensor_val.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay_read_sensor_val.addSpacerItem(QSpacerItem(0, 10))
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

        self.check_btn_read_sensor_value = QCheckBox(self.tr("Read Sensor Pressure Value"))
        lay_read_sensor_val.addWidget(self.check_btn_read_sensor_value)

    def initSignalCallback(self):
        self.btn_pcan_scan.clicked.connect(self.on_pcan_scan_btn_click)
        self.btn_pcan_init.clicked.connect(self.on_pcan_init_btn_click)
        self.btn_sensor_cal_add.clicked.connect(self.on_sensor_cal_add_btn_click)
        self.btn_sensor_cal_minus.clicked.connect(self.on_sensor_cal_minus_btn_click)
        self.btn_sensor_cal_sort.clicked.connect(self.on_sensor_cal_sort_btn_click)
        self.btn_load_cal.clicked.connect(self.on_load_btn_click)
        self.btn_save_cal.clicked.connect(self.on_save_btn_click)

        self.combo_edit_id.currentTextChanged.connect(self.on_scan_id_combo_change)
        self.btn_edit_id_scan.clicked.connect(self.on_edit_id_scan_click)
        self.btn_edit_id.clicked.connect(self.on_edit_id_btn_click)
        self.btn_read_id.clicked.connect(self.on_read_id_btn_click)
        self.btn_edit_freq.clicked.connect(self.on_edit_freq_btn_click)
        self.btn_read_freq.clicked.connect(self.on_read_freq_btn_click)
        self.btn_cal_save.clicked.connect(self.on_cal_save_btn_click)
        self.btn_plant_save.clicked.connect(self.on_plant_save_btn_click)
        self.btn_recover_plant.clicked.connect(self.on_recover_plant_btn_click)
        self.table_btn_delegate_acq.clicked.connect(self.on_table_acq_btn_click)
        self.check_btn_read_sensor_value.checkStateChanged.connect(self.on_check_box_pressure_value_switch)

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
            if channel.channel_condition & pCANBasic.PCAN_CHANNEL_AVAILABLE:
                items.append(self.FormatChannelName(channel.channel_handle,
                                                    channel.device_features & pCANBasic.FEATURE_FD_CAPABLE))

        self.combo_pacn_scan.addItems(items)

    def on_pcan_init_btn_click(self):
        if self.is_connect:
            self.stopWork()
            self.set_enable(False)
            self.drv.Uninitialize(self.pCanHandle)
            self.btn_pcan_init.setText(self.tr("Connect"))
            self.btn_pcan_init.setStyleSheet('''
            QPushButton {
                color: white;
                background-color: #0078D7;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }
            ''')
            self.is_connect = False
            return

        if self.combo_pacn_scan.count() == 0:
            QMessageBox.critical(self, self.tr("Error"), self.tr("The PCAN hardware was not found"))
            return

        baud_rate = self.pcan_baud_rate_list.get(self.combo_pcan_baud.currentText())
        hw_type = pCANBasic.PCAN_TYPE_ISA
        ioport = 0x100
        interrupt = 3
        strChannel = self.combo_pacn_scan.currentText()
        startIndex = strChannel.index("(") + 1
        strChannel = strChannel[startIndex:startIndex + 3]
        strChannel = strChannel.replace("h", "")
        self.pCanHandle = int(strChannel, 16)

        result = self.drv.Initialize(self.pCanHandle, baud_rate, hw_type, ioport, interrupt)
        if result != pCANBasic.PCAN_ERROR_OK:
            if result != pCANBasic.PCAN_ERROR_CAUTION:
                QMessageBox.critical(self, self.tr("Error"),
                                     str(self.GetFormatedError(result)) if type(result) == int else result)
            else:
                QMessageBox.warning(self, self.tr("warning"),
                                    self.tr("The bitrate being used is different than the given one"))
                result = pCANBasic.PCAN_ERROR_OK
        # else:
        #     iBuffer = 5
        #
        #     stsResult = self.drv.SetValue(self.pCanHandle, pCANBasic.PCAN_TRACE_SIZE, iBuffer)
        #     if stsResult != pCANBasic.PCAN_ERROR_OK:
        #         self.GetFormatedError(stsResult)
        #         # self.IncludeTextMessage(self.GetFormatedError(stsResult))
        #     iBuffer = TRACE_FILE_SINGLE | TRACE_FILE_OVERWRITE
        self.is_connect = result == pCANBasic.PCAN_ERROR_OK
        if self.is_connect:
            self.btn_pcan_init.setText(self.tr("Disconnect"))
            self.btn_pcan_init.setStyleSheet('''
            QPushButton {
                color: white;
                background-color: #ff7b72;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }
            ''')

            self.startWork()
        else:
            self.stopWork()
            self.btn_pcan_init.setText(self.tr("Connect"))

            self.btn_pcan_init.setStyleSheet('''
            QPushButton {
                color: white;
                background-color: #0078D7;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }
            ''')

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

    def on_save_btn_click(self):

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="保存配置文件",
            # dir=path,  # 初始目录
            filter="JSON Files (*.json)"
        )
        if file_path:
            js_data = self.sensorCalParamList.model_dump(mode="json", by_alias=True)
            js_file = json.dumps(js_data, indent=2)
            with open(file_path,'w',encoding="utf-8") as f:
                f.write(js_file)



    def on_load_btn_click(self):
        file, _ = QFileDialog.getOpenFileName(parent=self,
                                              caption="打开配置文件",
                                              filter="JSON Files (*.json)")
        if not file:
            return

        with open(file, "r") as data:
            read_file =  data.read()
        js_data = json.loads(read_file)
        self.sensorCalParamList = SensorCalParamList.model_validate(js_data)
        self.table_model.update(self.sensorCalParamList)




    def on_sensor_cal_sort_btn_click(self):
        self.sensorCalParamList.sort()
        self.table_model.update()

    def on_scan_id_combo_change(self, value):
        if self.combo_edit_id.count() == 0:
            self.current_can_id = -1
            return
        self.current_can_id = int(value)

    def on_edit_id_scan_click(self):
        if not self.is_scan_can_id:
            self.check_btn_read_sensor_value.setChecked(False)
            self.send_can_frame([Command.Switch, 0x01], True)

            self.is_scan_can_id = True
            self.scan_can_id_list.clear()
            QTimer.singleShot(500, lambda: self.on_scan_can_id(1))
            self.set_status_bar(0, self.tr("Scan Can Id:"))

    def on_scan_can_id(self, num: int):
        self.set_status_bar(100 / 4 * num, self.tr("Scan Can Id:"))

        if num >= 4:
            self.is_scan_can_id = False
            self.combo_edit_id.clear()
            self.set_status_bar(100 / 4 * num, self.tr("Scan Can Id:"), self.tr("Done"), True)
            if len(self.scan_can_id_list) > 0:
                self.combo_edit_id.addItems(self.scan_can_id_list)
                self.spin_edit_id.setValue(int(self.combo_edit_id.currentText()))
                self.current_can_id = int(self.combo_edit_id.currentText())
                return
            self.current_can_id = -1
            print("scan can id stop")
            return

        QTimer.singleShot(500, lambda: self.on_scan_can_id(num + 1))

    def on_edit_id_btn_click(self):
        if not self.is_connect:
            return

        self.send_can_frame([Command.ID, self.spin_edit_id.value()])

    def on_read_id_btn_click(self):
        pass

    def on_edit_freq_btn_click(self):
        if not self.is_connect:
            return

        # if self.current_can_id == -1:
        #     QMessageBox.critical(self, self.tr("Error"), self.tr("The pressure sensor was not scanned"))
        #     return

        self.send_can_frame([Command.Freq, int(self.combo_edit_freq.currentText()[:-2])])

    def on_read_freq_btn_click(self):
        pass

    def on_edit_sn_btn_click(self):
        pass

    def on_read_sn_btn_click(self):
        pass

    def on_cal_save_btn_click(self):
        self.sensorCalParamList.sort()
        self.table_model.update()
        QTimer.singleShot(10, lambda: self.on_cal_save_qtimer(0))
        self.set_status_bar(0, self.tr("Save Cal Data:"))

    def on_cal_save_qtimer(self, index):
        if index >= len(self.sensorCalParamList.sensorCalParam):
            result = self.send_can_frame([Command.Switch, 0x02])
            self.set_status_bar(100 / len(self.sensorCalParamList.sensorCalParam) * index, self.tr("Save Cal Data:"),
                                self.tr("Done"), True)

            return

        param = self.sensorCalParamList.sensorCalParam[index]
        data = [0] * 8
        data[0] = Command.Cal
        data[1] = index
        data[2] = param.adValue & 0xFF
        data[3] = (param.adValue >> 8) & 0xFF
        data[4] = (param.adValue >> 16) & 0xFF
        data[5] = (param.adValue >> 24) & 0xFF
        data[6] = param.rangeValue & 0xFF
        data[7] = (param.rangeValue >> 8) & 0xFF
        result = self.send_can_frame(data)
        if result == pCANBasic.PCAN_ERROR_OK:
            QTimer.singleShot(10, lambda: self.on_cal_save_qtimer(index + 1))
            self.set_status_bar(100 / len(self.sensorCalParamList.sensorCalParam) * index, self.tr("Save Cal Data:"))
        else:
            self.set_status_bar(100 / len(self.sensorCalParamList.sensorCalParam) * index, self.tr("Save Cal Data:"),
                                self.tr("Failure"), True, False)

    def on_plant_save_btn_click(self):
        self.send_can_frame([Command.Save])

    def on_recover_plant_btn_click(self):
        self.send_can_frame([Command.Reset])


    def on_table_acq_btn_click(self, index: QModelIndex):
        self.sensorCalParamList.sensorCalParam[index.row()].adValue = self.current_sensor_ad_value
        self.table_model.update()

    def on_check_box_pressure_value_switch(self, value):
        # self.check_data_base(20)

        if value == Qt.CheckState.Checked:
            self.send_can_frame([Command.Switch, 0x00], True)
        else:
            self.send_can_frame([Command.Switch, 0x01], True)
            self.sensorCalParamList.sort()
            self.table_model.update()


    def on_worker_result_callback(self, result):
        if len(result) == 0:
            return

        for msg in result:
            if not tool.can_id_check_gression_700(msg[0].ID):
                continue

            canId = tool.can_id_remove_gression(msg[0].ID)
            data = msg[0].DATA

            if self.is_scan_can_id and (str(canId) not in self.scan_can_id_list):
                self.scan_can_id_list.append(str(canId))

            if canId != self.current_can_id:
                continue

            if self.check_btn_read_sensor_value.isChecked() and msg[0].LEN == 2:
                sensorValue = tool.remove_gression_high_3(data[0], data[1])
                self.text_read_sensor_value.setText(str(sensorValue))
            else:
                adValue = tool.merge_int8_to_int32(data)
                self.current_sensor_ad_value = adValue
                self.text_read_ad_value.setText(str(adValue))

                index_1, index_2 = self.check_data_base(adValue)
                if index_1 == -1:
                    self.text_read_sensor_value.setText("Error")

                elif index_1 == index_2:
                    self.text_read_sensor_value.setText(str(self.sensorCalParamList.sensorCalParam[index_1].rangeValue))
                else:
                    # y = m*x+b
                    x1, x2, y1, y2 = (self.sensorCalParamList.sensorCalParam[index_1].adValue,
                                      self.sensorCalParamList.sensorCalParam[index_2].adValue,
                                      self.sensorCalParamList.sensorCalParam[index_1].rangeValue,
                                      self.sensorCalParamList.sensorCalParam[index_2].rangeValue)

                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1

                    value = m * adValue + b
                    self.text_read_sensor_value.setText(f'%.2f' % value)

            # print(adValue)

        # print(result)

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

    def GetFormatedError(self, error):
        # Gets the text using the GetErrorText API function
        # If the function success, the translated error is returned. If it fails,
        # a text describing the current error is returned.
        #
        stsReturn = self.drv.GetErrorText(error, 0)
        if stsReturn[0] != pCANBasic.PCAN_ERROR_OK:
            return "An error occurred. Error-code's text ({0:X}h) couldn't be retrieved".format(error)
        else:
            return stsReturn[1]

    def readMsg(self):
        stsResult = pCANBasic.PCAN_ERROR_OK
        results = []
        while self.pCanHandle and not (stsResult & pCANBasic.PCAN_ERROR_QRCVEMPTY):
            result = self.drv.Read(self.pCanHandle)
            stsResult = result[0]
            if result[0] == pCANBasic.PCAN_ERROR_OK:
                results.append(result[1:])
            elif result[0] & pCANBasic.PCAN_ERROR_ILLOPERATION:
                break
        return results

    def send_can_frame(self, data: list, is_broadcast=False):
        canMsg = pCANBasic.TPCANMsg()
        if is_broadcast:
            canMsg.ID = tool.can_id_generate_gression_300(self.broadcast_id)
        else:
            if self.is_broadcast:
                canMsg.ID = tool.can_id_generate_gression_300(self.broadcast_id)
            else:
                if self.current_can_id == -1:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("The pressure sensor was not scanned"))
                    return
                canMsg.ID = tool.can_id_generate_gression_300(self.current_can_id)

        canMsg.LEN = 8
        canMsg.MSGTYPE = pCANBasic.PCAN_MESSAGE_STANDARD

        for i in range(8):
            if i < len(data):
                canMsg.DATA[i] = data[i]
            else:
                canMsg.DATA[i] = 0

        result = self.drv.Write(self.pCanHandle, canMsg)
        if result != pCANBasic.PCAN_ERROR_OK:
            QMessageBox.critical(self, self.tr("Error"),
                                 str(self.GetFormatedError(result)) if type(result) == int else result)

        return result

    def set_status_bar(self, progress, info, info_done="", is_done=False, state=True):

        if is_done:
            self.status_bar_progress.hide()
            self.status_bar_label.hide()
            self.statusBar().showMessage(info_done, 1500)
            return
        if state:
            self.status_bar_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #02913a;
                width: 50px;
            }
            """)
        else:
            self.status_bar_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #ff0000;
                width: 50px;
            }
            """)

        self.status_bar_label.setText(info)
        self.status_bar_progress.setValue(progress)
        self.status_bar_progress.show()
        self.status_bar_label.show()

    def check_data_base(self, value):
        ad_values = [param.adValue for param in self.sensorCalParamList.sensorCalParam]
        ge_index = bisect.bisect_left(ad_values, value)  # 第一个 >= value 的位置
        le_index = bisect.bisect_right(ad_values, value) - 1  # 最后一个 <= value 的位置
        if ge_index >= len(self.sensorCalParamList.sensorCalParam):
            ge_index = -1
        if le_index < 0:
            le_index = -1
        # print(ad_values[le_index], value, ad_values[ge_index])

        return ge_index, le_index

    def set_enable(self,enable):
        self.box_sensor_set.setEnabled(enable)
        self.btn_plant_save.setEnabled(enable)
        self.btn_cal_save.setEnabled(enable)
        self.btn_recover_plant.setEnabled(enable)

    def startWork(self):

        if self.workThread and self.workThread.isRunning():
            return
        self.set_enable(True)
        self.send_can_frame([Command.Switch, 0x01], True)
        self.check_btn_read_sensor_value.setChecked(False)
        self.current_sensor_ad_value = 0
        self.current_can_id = -1
        self.is_scan_can_id = True
        self.scan_can_id_list.clear()
        QTimer.singleShot(500, lambda: self.on_scan_can_id(1))
        self.set_status_bar(0, self.tr("Scan Can Id:"))

        self.workThread = QThread()
        self.worker = ReadCanMsgWork(self.readMsg)
        self.worker.moveToThread(self.workThread)
        self.workThread.started.connect(self.worker.start_work)
        self.worker.finishedSignal.connect(self.workThread.quit)
        self.worker.finishedSignal.connect(self.worker.deleteLater)
        self.workThread.finished.connect(self.workThread.deleteLater)
        self.workThread.finished.connect(self._work_finished_cleanup)

        self.worker.resultSignal.connect(self.on_worker_result_callback)
        self.workThread.start()

    def stopWork(self):
        if self.worker:
            self.worker.stop_work()
        if self.workThread:
            self.workThread.quit()
            self.workThread.wait()

    def _work_finished_cleanup(self):
        self.worler = None
        self.workThread = None

    def check_admin(self):
        path = os.path.join(os.getcwd(), ".admin")
        if not os.path.isfile(path):
            self.is_admin = False
            return

        self.is_admin = True

    def closeEvent(self, event, /):
        self.stopWork()
        event.accept()
