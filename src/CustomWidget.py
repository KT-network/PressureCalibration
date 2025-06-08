# -*- coding: utf-8 -*-
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (QTableView, QStyledItemDelegate, )

from .dataModel import SensorCalParam, SensorCalParamList


class CustomTableModel(QAbstractTableModel):

    def __init__(self, header: list, data: SensorCalParamList, parent=None):
        super().__init__(parent)
        self._header_label: list = header
        self._data: SensorCalParamList = data

    def rowCount(self, /, parent=...):
        if hasattr(self, "_data"):
            return len(self._data.sensorCalParam)
        return 0

    def columnCount(self, index=QModelIndex()):
        return len(self._header_label)

    def data(self, index, /, role=...):
        if not index.isValid():
            return None

        param: SensorCalParam = self._data.sensorCalParam[index.row()]


        if (role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole) and index.column() in (0, 1):
            if index.column() == 0:
                return param.adValue
            elif index.column() == 1:
                return param.rangeValue
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter  # 设置内容居中

    def setData(self, index, value, /, role=...):
        if not index.isValid():
            return False
        param = self._data.sensorCalParam[index.row()]
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                param.adValue = value
            elif index.column() == 1:
                param.rangeValue = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index, /):
        flag = super().flags(index)

        if index.column() != 2:
            return flag | Qt.ItemFlag.ItemIsEditable
            # return flag | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return flag

    def headerData(self, section, orientation, role=...):

        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._header_label[section]
        elif orientation == Qt.Orientation.Vertical:
            return str(section + 1)
        return None

    def setHeaderData(self, section, orientation, value, role=...):
        if role == Qt.ItemDataRole.EditRole and orientation == Qt.Orientation.Horizontal:
            self._header_label[section] = value
            self.headerDataChanged.emit(Qt.Orientation.Horizontal, section, section)
            return True
        return False

    def update(self,data=None):
        self.beginResetModel()
        if data !=None:
            self._data = data
        self.endResetModel()

    def removeRow(self, row, /, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        self._data.sensorCalParam.pop(row)
        self.endRemoveRows()
        return True


class CustomTableAcqButtonDelegate(QStyledItemDelegate):
    clicked = Signal(QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def paint(self, painter, option, index):
        # 绘制标准单元格
        # super().paint(painter, option, index)

        rect = option.rect
        button_text = self.tr("Acquisition")
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         button_text)

    def editorEvent(self, event, model, option, index):
        if event.type() == QMouseEvent.Type.MouseButtonRelease:
            rect = option.rect
            if rect.contains(event.pos()):
                self.clicked.emit(index)
                return True

        return super().editorEvent(event, model, option, index)


class CustomTableView(QTableView):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.header_label = [self.tr("AD value"), self.tr("Physical value")]

    def initModel(self):
        self.verticalHeader().setHidden(True)
        self._model = CustomTableModel(self.header_label)
        self.setModel(self._model)

    # def setData(self):
