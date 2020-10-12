from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (QMainWindow, QStyledItemDelegate, QComboBox)
from PyQt5.QtCore import (Qt, QAbstractTableModel, QModelIndex)
from PyQt5.QtGui import QFont, QColor

import numpy as np
# Импортируем форму.
from qtable2 import Ui_Main_Window
import h5py
from tkinter import *
import pyqtgraph as pg

col_count = 4  # зафиксированное количество столбцов
colRnd = 0  # номер столбца, в котором будут рандомные значения
colCBox = 1  # номер столбца, в котором будут выпадающие списки
colRecount = 2   # номер столбца, в котором будут пересчитываемые значения
colAccum = 3  # номер столбца, в котором будут накапливаемые значения


class NpModel(QAbstractTableModel):
    def __init__(self, data=np.array([[]]), parent=None):
        super().__init__()
        self.npdata = data

    def rowCount(self, index=QModelIndex()):  # число строк
        return len(self.npdata)

    def columnCount(self, index=QModelIndex()):  # число столбцов
        return len(self.npdata[0])

    def data(self, index, role):
        if not index.isValid(): return None
        row = index.row()
        col = index.column()
        val = self.npdata[row, col]  # значения по индексу
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 1:  # выводим целочисленные значения комбобоксов
                return str(round(val, 0)).replace('.0', '')
            else:  # значения остальных колонок округлили
                return str(round(val, 3))
        elif role == Qt.BackgroundRole:
            if col == 0:  # заливка красным/зеленым для положительного/отрицательного значения
                if val > 0:
                    return QColor(255, 0, 0, 100)  # 100 - прозрачность
                else:
                    return QColor(0, 255, 0, 100)

    def flags(self, index):
        if index.column() == 0:  # разрешили выделение и редактирование
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        if index.column() == 1:  # разрешили редактирование
            return Qt.ItemIsEnabled | Qt.ItemIsEditable
        if index.column() >= 2:  # запретили редактирование, только выделение
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index, value, role):  # занесли данных в массив npdata
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            try:
                if index.column() == 0:
                    f = float(value.replace(',', '.'))
                elif index.column() == 1:  # округляем значения для столбца с комбобоксом
                        f = round(value, 0)
                else:
                    return False
            except:
                return False
            self.npdata[index.row(), index.column()] = f  # занесли данные в массив
            self.dataChanged.emit(index, index)
            self.set_recount_data(index.row(), 1)  # заново вызвали функции пересчета
            self.accumulation_data(index.row(), 1)  # и накопления
            return True
        return False

    def headerData(self, section, orientation, role):  # установка заголовков таблицы
        col_headers = ["Рандом кр/зел", "Вып. список", "Пересчет", "Накопление"]
        if role != Qt.DisplayRole: return None
        if orientation == Qt.Horizontal:
            return col_headers[section]
        else:
            return str(section + 1)

    def load(self, arr):  # загрузка данных в массив из другого массива
        self.beginResetModel()
        self.npdata = arr
        self.endResetModel()

    def load_rnd_data(self, start_row_for_0_col: int, start_row_for_1_col: int, row_count_to_change: int):
        # заполняем столбец с случайными значениями
        self.beginResetModel()
        items = np.random.random(row_count_to_change) * 100 - 50  # рандом от -50 до 50
        self.npdata[start_row_for_0_col:, colRnd] = items
        self.npdata[start_row_for_1_col:, 1] = 1
        self.accumulation_data(start_row_for_0_col, row_count_to_change)  # после заполнения столбца с рандомом заполняем столбцы
        self.set_recount_data(start_row_for_0_col, row_count_to_change)  # с пересчитываемыми и накапливаемыми значениями
        self.endResetModel()

    def save_txt_data(self) -> NONE:  # сохранение данных в txt-файл
        f = open('data.txt', 'w')
        # 'w' открытие на запись, содержимое файла удаляется, если файла не существует, создается новый.
        np.savetxt('data.txt', self.npdata)
        f.close()

    def load_txt_data(self) -> int:  # загрузка данных из файла txt
        f = open('data.txt')
        row_count_txt = sum(1 for _ in f)  # определение количества строк в файле
        f.close()
        self.load(np.zeros((row_count_txt, col_count)))
        if row_count_txt == 1:  # если в файле 1 строка, используем одномерный массив
            temp_data = np.zeros(col_count)
            temp_data = np.loadtxt("data.txt", usecols=(0, 1, 2, 3))
            self.beginResetModel()
            self.npdata[0, :] = temp_data
            self.endResetModel()
        else:
            self.beginResetModel()
            self.npdata = np.loadtxt("data.txt", usecols=(0, 1, 2, 3))  # считали данные из файла
            self.endResetModel()
        return row_count_txt

    def save_hdf_data(self) -> NONE:  # сохранение данных в hdf-файл
        with h5py.File('random.hdf5', 'w') as fw:
            dset = fw.create_dataset("default", (self.rowCount(QModelIndex()), col_count))  # data=data)
            dset[:] = self.npdata

    def load_hdf_data(self) -> int:  # загрузка данных из файла hdf
        self.beginResetModel()
        with h5py.File('random.hdf5', 'r') as fr:
            self.npdata = fr['default'][:]  # считали данные из файла
        self.endResetModel()
        row_count_hdf = self.npdata.shape[0]
        return row_count_hdf

    def set_recount_data(self, start_row: int, row_count_to_change: int) -> np:  # заполняем столбец с пересчитываемыми
        # значениями (в основе значения из рандома)
        self.npdata[start_row:start_row + row_count_to_change, colRecount] \
            = self.npdata[start_row:start_row + row_count_to_change, colRnd] \
            * self.npdata[start_row:start_row + row_count_to_change, colRnd] + 10
        return self.npdata

    def accumulation_data(self, start_row: int, row_count_to_change: int) -> np:  # заполняем столбец с накопл. знач-ми
        self.npdata[start_row:start_row + row_count_to_change, colAccum] \
            += self.npdata[start_row:start_row + row_count_to_change, colRnd]  # накопление
        # на основе столбца с рандомными значениями
        return self.npdata

    def new_size(self, old_row_count, new_row_count):
        self.beginResetModel()
        if new_row_count > old_row_count:  # если необходимо добавить новые строки,
            # вызываются функции, которые заполнят новые строки новыми значениями
            diff_row_count = new_row_count - old_row_count
            tmp_data = np.zeros((diff_row_count, col_count))
            self.npdata = np.vstack((self.npdata, tmp_data))  # соединили два массива в один
            self.load_rnd_data(old_row_count, old_row_count, diff_row_count)  # добавление рандомных значений
            self.set_recount_data(old_row_count, diff_row_count)  # добавление пересчитываемых значений
        elif new_row_count < old_row_count:
            # если новое число строк меньше старого, то удаляем нижние строки из массива
            self.npdata = self.npdata[:new_row_count, ]
        self.endResetModel()


class ComboBoxDelegate(QStyledItemDelegate):  # класс для добавления комбобоксов
    def createEditor(self, parent, option, index):  # создаем и заполняем комбобоксы
        editor = QComboBox(parent)
        editor.addItems(["1", "2", "3", "4", "5"])
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor, index):  # определение позиции текущего значения в списке комбобокса
        value = index.model().data(index, Qt.EditRole)
        editor.setCurrentIndex(editor.findText(value))

    def setModelData(self, editor, model, index):  # заносим выбранное значение комбобокса в массив
        model.setData(index, int(editor.currentIndex() + 1), Qt.EditRole)


class MyWindow(QMainWindow):

    def __init__(self, data=np.array([[]])):
        self.model = NpModel(data)
        #  конструктор класса
        QMainWindow.__init__(self)
        self.first_row_count = 4  # первоначальное количество строк
        self.row_count_txt = 0  # количество строк в файле txt
        self.row_count_hdf = 0  # количество строк в файле hdf
        self.selected_col_X = -1  # номер выбранного столбца для построения графика (Ох)
        self.selected_col_Y = -1  # номер выбранного столбца для построения графика (Оу)
        self.row_count = self.first_row_count  # общее число строк
        self.ui = Ui_Main_Window()
        self.ui.setupUi(self)
        self.ui.resize_button.clicked.connect(self.resize_btn_clicked)  # кнопка изменения размера массива
        self.ui.save_new_size.clicked.connect(self.save_resize_btn_clicked)  # кнопка сохранения размера массива
        self.ui.random_button.clicked.connect(self.rnd_btn_clicked)  # кнопка рандомного заполнения одного столбца
        self.ui.save_txt_button.clicked.connect(self.model.save_txt_data)  # кнопка сохранения в txt
        self.ui.load_from_txt_button.clicked.connect(self.load_txt_data)  # кнопка загрузки из txt
        self.ui.save_hdf_button.clicked.connect(self.model.save_hdf_data)  # кнопка сохранения в hdf
        self.ui.load_from_hdf_button.clicked.connect(self.load_hdf_data)  # кнопка загрузки из hdf
        self.ui.graph_btn.clicked.connect(self.graph)
        self.ui.list_col_combo.currentTextChanged.connect(self.set_column_to_graph)
        self.ui.spinBoxSize.setEnabled(False)  # заблокировали окно ввода
        self.ui.save_new_size.setEnabled(False)  # заблокировали кнопку сохранения размера массива
        self.view = view = pg.PlotWidget()  # добавили и настроили поле для отражения графика
        self.view.setBackground('w')
        self.ui.gridLayout_3.addWidget(self.view, 1, 0, 1, 1)
        self.curve = view.plot(pen=pg.mkPen('k', width=2), name="Graph")
        # Первая загрузка
        self.ui.tableView.setItemDelegateForColumn(1, ComboBoxDelegate())
        self.ui.tableView.setModel(self.model)
        self.ui.tableView.setFont(QFont('Times', 14))
        self.ui.tableView.resize(800, 500)
        self.model.load_rnd_data(0, 0, self.first_row_count)

    def set_column_to_graph(self):  # определяем выбранные колонки для построения графика
        select_pos = self.ui.list_col_combo.currentIndex()
        select_text = self.ui.list_col_combo.currentText()
        if select_pos == 1:
            self.selected_col_X = 0
            self.selected_col_Y = 2
        elif select_pos == 2:
            self.selected_col_X = 0
            self.selected_col_Y = 3
        elif select_pos == 3:
            self.selected_col_X = 2
            self.selected_col_Y = 3
        elif select_pos == 4:
            self.selected_col_X = 2
            self.selected_col_Y = 0
        elif select_pos == 5:
            self.selected_col_X = 3
            self.selected_col_Y = 0
        elif select_pos == 6:
            self.selected_col_X = 3
            self.selected_col_Y = 2
        else:
            self.selected_col_X = -1
            self.selected_col_Y = -1

    def resize_btn_clicked(self):  # кнопка, разблокирующая ввод нового размера массива
        self.ui.spinBoxSize.setEnabled(True)  # разблокировали окно ввода
        self.ui.save_new_size.setEnabled(True)  # разблокировали окно ввода
        self.ui.save_txt_button.setEnabled(False)  # заблокировали ненужные при вводе размера кнопки
        self.ui.save_hdf_button.setEnabled(False)
        self.ui.load_from_txt_button.setEnabled(False)
        self.ui.load_from_hdf_button.setEnabled(False)
        self.ui.resize_button.setEnabled(False)
        self.ui.random_button.setEnabled(False)
        self.ui.spinBoxSize.setFocus()  # установка курсора в начало окошка для ввода

    def save_resize_btn_clicked(self) -> int:  # сохранение нового размера массива
        old_row_count = self.row_count  # сохранили старое кол-во строк
        new_row_count = self.ui.spinBoxSize.value()  # позволяет задать значения 1-999999
        self.model.new_size(old_row_count, new_row_count)
        self.row_count = new_row_count
        self.ui.spinBoxSize.setEnabled(False)  # заблокировали окно ввода
        self.ui.save_new_size.setEnabled(False)  # заблокировали кнопку сохранения размера массива
        self.ui.save_txt_button.setEnabled(True)  # разблокировали остальные кнопки
        self.ui.save_hdf_button.setEnabled(True)
        self.ui.load_from_txt_button.setEnabled(True)
        self.ui.load_from_hdf_button.setEnabled(True)
        self.ui.random_button.setEnabled(True)
        self.ui.resize_button.setEnabled(True)
        self.graph()  # если график ранее строился, то построим его по прежним колонкам
        return self.row_count

    def load_txt_data(self) -> np:
        self.row_count = self.model.load_txt_data()

    def load_hdf_data(self) -> np:
        self.row_count = self.model.load_hdf_data()

    def rnd_btn_clicked(self) -> np:  # перезаполнили первый столбец рандомными числами
        self.model.load_rnd_data(0, self.row_count, self.row_count)
        self.graph()  # если график ранее строился, то построим его по прежним колонкам
        return self.model.npdata

    def graph(self) -> NONE:
        if (self.selected_col_X != -1) and (self.selected_col_Y != -1):
            col_x = self.selected_col_X  # выбранные пользователем колонки в качестве x и y
            col_y = self.selected_col_Y
            self.curve.setData(self.model.npdata[:, col_x], self.model.npdata[:, col_y])  # задали построение графика
            #  по данным из таблицы
            x_name = str(col_x + 1)  # подпись к оси Ох
            y_name = str(col_y + 1)  # подпись к оси Оу
            self.view.setLabel('left', "Y Axis " + y_name + " column")  # вывели подпись к оси Ох
            self.view.setLabel('bottom', "X Axis " + x_name + " column")  # вывели подпись к оси Оу
        else:
            self.curve.setData([0], [0])  # задали построение графика
            self.view.setLabel('left', "Y Axis 0 column")  # вывели подпись к оси Ох
            self.view.setLabel('bottom', "X Axis 0 column")  # вывели подпись к оси Оу


app = QtWidgets.QApplication([])
first_row_count = 4
data = np.zeros((first_row_count, col_count))  # создали двумерный массив из нулей
data[:, 1] = 1
application = MyWindow(data)
application.show()
sys.exit(app.exec())
