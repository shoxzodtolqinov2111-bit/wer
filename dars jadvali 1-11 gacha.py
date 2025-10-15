# Dars jadvali yaratish uchun zarur bo'lgan kutubxonalarni import qilish
import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QProgressBar,
    QListWidget, QTextEdit, QMessageBox, QComboBox, QListWidget,
    QSpinBox
)
from PySide6.QtCore import QThreadPool, QObject, Signal, Slot, QRunnable
import pandas as pd
import random
import os
import logging
import json
import threading
from typing import Dict, List, Tuple
from collections import defaultdict
import traceback  # traceback import qilindi

# Dastur konfiguratsiyasi
# Sinf smenalar soni
NUMBER_OF_SESSIONS = 2
# Bir smenada bo'lishi mumkin bo'lgan maksimal o'quvchilar soni
MAX_STUDENTS_PER_SESSION = 300
# Hafta kunlari ro'yxati
DAYS_OF_WEEK = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"]
# Excel fayl nomi
EXCEL_FILENAME = "Dars_jadvali.xlsx"

# Bo'sh xona topish funksiyasi
def find_available_room(rooms: Dict[str, int], class_size: int) -> str:
    """
    Sinf o'lchamiga mos keladigan bo'sh xonani topadi.

    Args:
        rooms: Xonalar va ularning sig'imlari haqidagi ma'lumotlar
        class_size: Sinf o'lchami

    Returns:
        Mos xona topilsa uning ID si, aks holda None
    """
    for room, capacity in rooms.items():
        if capacity >= class_size:
            return room
    return None

# Jadval modeli
class ScheduleModel:
    def __init__(self):
        """
        Jadval modelini boshlang'ich holatda ishga tushiradi.
        Barcha kerakli o'zgaruvchilar va tuzilmalarni yaratadi.
        """
        self.user_classes: List[str] = []  # Sinflar ro'yxati
        self.weekly_hours_by_grade: Dict[int, Dict[str, int]] = self.get_weekly_hours()
        self.class_rooms: Dict[str, int] = {}  # Xonalar va ularning sig'imlari
        self.class_sizes: Dict[str, int] = {}  # Sinflar va ularning o'lchamlari
        self.operation_in_progress = False  # Amal bajarilayotganligini ko'rsatuvchi flag
        self.lock = threading.Lock()  # Thread xavfsizligi uchun qulflash
        self.session_classes: Dict[str, List[str]] = {f"{i+1}-smena": [] for i in range(NUMBER_OF_SESSIONS)}
        self.session_capacities: Dict[str, int] = {f"{i+1}-smena": 0 for i in range(NUMBER_OF_SESSIONS)}
        self.schedule_constraints = defaultdict(list)  # Jadval cheklovlarini saqlash uchun
        self.subject_rooms: Dict[str, str] = {} # Fanlar va xonalar lug'ati
        self.custom_classes = {}  # 1-4 sinflar uchun fanlar va soatlar (qo'lda kiritiladi)
        self.teachers = {}  # O'qituvchilar va ularga biriktirilgan sinflar

    def get_weekly_hours(self) -> Dict[int, Dict[str, int]]:
        """
        Har bir sinf uchun haftalik dars soatlarini qaytaradi.

        Returns:
            Sinflar va ularning fanlari bo'yicha haftalik soatlar soni
        """
        return {
            5: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Tabiat fani": 2, "Tarix": 2, "Matematika": 5,
                "Rasm": 1, "Texnologiya": 2, "Jismoniy tarbiya": 2, "Informatika": 1, "Tarbiya": 1, "Musiqa": 1},
            6: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Tabiat fani": 2, "Tarix": 2, "Matematika": 5,
                "Rasm": 1, "Texnologiya": 2, "Jismoniy tarbiya": 2, "Informatika": 1, "Tarbiya": 1, "Musiqa": 1},
            7: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Ingliz tili": 3, "Fizika": 2, "Kimyo": 2,
                "Biologiya": 2, "Geografiya": 2, "Matematika": 5, "Rasm": 1, "Texnologiya": 2, "Jismoniy tarbiya": 2,
                "Informatika": 1, "Tarbiya": 1, "Jahon tarixi": 1, "O'zbekiston tarixi": 2, "Musiqa": 1},
            8: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Ingliz tili": 3, "Fizika": 2, "Kimyo": 2,
                "Biologiya": 2, "Geografiya": 2, "Algebra": 3, "Geometriya": 2, "Chizmachilik": 1, "Texnologiya": 1,
                "Jismoniy tarbiya": 2, "Informatika": 2, "Tarbiya": 1, "Huquq": 1, "Jahon tarixi": 1,
                "O'zbekiston tarixi": 2},
            9: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Ingliz tili": 3, "Fizika": 2, "Kimyo": 2,
                "Biologiya": 2, "Geografiya": 2, "Algebra": 3, "Geometriya": 2, "Chizmachilik": 1, "Texnologiya": 1,
                "Jismoniy tarbiya": 2, "Informatika": 2, "Tarbiya": 1, "Huquq": 1, "Jahon tarixi": 1,
                "O'zbekiston tarixi": 2, "Ch.Q.B.T": 1},
            10: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Ingliz tili": 3, "Fizika": 2, "Kimyo": 2,
                "Biologiya": 2, "Geografiya": 2, "Algebra": 3, "Geometriya": 2, "Jismoniy tarbiya": 2,
                "Informatika": 2, "Tarbiya": 1, "Huquq": 1, "Jahon tarixi": 1, "O'zbekiston tarixi": 2,
                "Ch.Q.B.T": 1},
            11: {"Ona tili": 3, "Adabiyot": 2, "Rus tili": 2, "Ingliz tili": 3, "Fizika": 2, "Kimyo": 2,
                "Biologiya": 2, "Geografiya": 2, "Algebra": 3, "Geometriya": 2, "Astronomiya": 1,
                "Jismoniy tarbiya": 2, "Informatika": 2, "Tarbiya": 1, "Huquq": 1, "Jahon tarixi": 1,
                "O'zbekiston tarixi": 2, "Ch.Q.B.T": 1}
        }

    def add_class(self, class_name: str, class_size: int) -> None:
        """
        Yangi sinfni qo'shish funksiyasi.

        Args:
            class_name: Sinf nomi (masalan: "7a")
            class_size: Sinfdagi o'quvchilar soni
        """
        with self.lock:
            if not isinstance(class_name, str) or not class_name:
                raise ValueError("Sinf nomi to'ldirilishi shart.")
            if not isinstance(class_size, int) or class_size <= 0:
                raise ValueError("Sinf hajmi musbat son bo'lishi shart.")
            self.user_classes.append(class_name)
            self.class_sizes[class_name] = class_size
            logging.info(f"{class_name} ({class_size} o'quvchi) qo'shildi.")

    def add_class_room(self, room_id: str, capacity: int, subject: str) -> None:
        """
        Yangi xona qo'shish funksiyasi.

        Args:
            room_id: Xona raqami (masalan: "201")
            capacity: Xona sig'imi
            subject: Xona qaysi fanga tegishli
        """
        with self.lock:
            if not isinstance(room_id, str) or not room_id:
                raise ValueError("Xona ID to'ldirilishi shart.")
            if not isinstance(capacity, int) or capacity <= 0:
                raise ValueError("Xona sig'imi musbat son bo'lishi shart.")
            self.class_rooms[room_id] = capacity
            self.subject_rooms[subject] = room_id
            logging.info(f"{room_id} ({capacity} sig'im) {subject} fani uchun qo'shildi.")

    def assign_subjects_to_classes(self, user_classes: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Sinflarga fanlar va ularning haftalik soatlarini biriktirish.

        Args:
            user_classes: Sinflar ro'yxati

        Returns:
            Har bir sinf uchun fanlar va ularning soatlar soni
        """
        class_subjects = {}
        for class_name in user_classes:
            try:
                with self.lock:
                    grade = int(''.join(filter(str.isdigit, class_name)))
                    if grade not in self.weekly_hours_by_grade:
                        raise ValueError(f"{class_name} uchun dars jadvali topilmadi.")
                    base_subjects = self.weekly_hours_by_grade[grade].copy()

                    if class_name in self.class_sizes and self.class_sizes[class_name] > 25:
                        for subject in ['Rus tili', 'Ingliz tili', 'Informatika']:
                            if subject in base_subjects:
                                base_subjects[subject] = base_subjects[subject] // 2

                    class_subjects[class_name] = base_subjects
                    logging.info(f"{class_name} ga fanlar biriktirildi: {class_subjects[class_name]}")

            except ValueError as e:
                logging.error(f"Fan biriktirishda xatolik: {str(e)}")
                raise

        return class_subjects

    def allocate_classes_to_sessions(self) -> None:
        """
        Sinflarni smenaga taqsimlash funksiyasi.
        Sinflar o'quvchilar soni chegarasiga qarab smenaga ajratiladi.
        """
        all_classes = list(self.user_classes)
        self.session_capacities = {f"{i + 1}-smena": 0 for i in range(NUMBER_OF_SESSIONS)}
        self.session_classes = {f"{i + 1}-smena": [] for i in range(NUMBER_OF_SESSIONS)}
        for class_name in all_classes:
            class_size = self.class_sizes.get(class_name, 0)
            assigned = False
            for i in range(NUMBER_OF_SESSIONS):
                smena = f"{i+1}-smena"
                if self.session_capacities[smena] + class_size <= MAX_STUDENTS_PER_SESSION:
                    self.session_classes[smena].append(class_name)
                    self.session_capacities[smena] += class_size
                    assigned = True
                    break
            if not assigned:
                logging.warning(f"Sinf {class_name} hech bir smenaga sig'maydi. Sinf hajmi: {class_size}")

    def create_weekly_schedule(self, class_subjects: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, List[str]]]:
        """
        Haftalik dars jadvalini yaratish funksiyasi.

        Args:
            class_subjects: Sinflar va ularning fanlari haqidagi ma'lumotlar

        Returns:
            Har bir sinf uchun haftalik dars jadvali
        """
        weekly_schedule = {}
        self.allocate_classes_to_sessions()

        for class_name, class_subjects in class_subjects.items():
            # Agar 1-4 sinf bo'lsa, qo'lda kiritilgan fanlarni olamiz
            if class_name in self.custom_classes:
                class_subjects = self.custom_classes[class_name]
            class_schedule = self._create_class_schedule(class_name, class_subjects)
            if class_schedule:
                weekly_schedule[class_name] = class_schedule
        return weekly_schedule

    def _create_class_schedule(self, class_name: str, class_subjects: Dict[str, int]) -> Dict[str, List[str]]:
        """
        Bitta sinf uchun dars jadvalini yaratish funksiyasi.

        Args:
            class_name: Sinf nomi
            class_subjects: Sinf uchun fanlar va ularning soatlar soni

        Returns:
            Hafta kunlari bo'yicha dars jadvali
        """
        daily_lessons: Dict[str, List[str]] = {day: [] for day in DAYS_OF_WEEK}
        try:
            klass_size = self.class_sizes.get(class_name, 20)
            all_lessons = []
            for subject, hours in class_subjects.items():
                available_room = self.subject_rooms.get(subject)
                if available_room is None:
                    logging.warning(f"{class_name} sinfi uchun {subject} fani uchun xona topilmadi!")
                    available_room = 'Noma\'lum xona'  # Agar xona topilmasa, standart qiymat

                all_lessons.extend([(subject, available_room)] * hours)

            # Numpy dan foydalanib tasodifiy tartibni yaratish
            np.random.shuffle(all_lessons)
            day_index = 0
            while all_lessons:
                subject, room = all_lessons.pop()
                day = DAYS_OF_WEEK[day_index]
                if f"{subject} ({room})" not in daily_lessons[day]:
                    daily_lessons[day].append(f"{subject} ({room})")
                day_index = (day_index + 1) % len(DAYS_OF_WEEK)
            return daily_lessons

        except Exception as e:
            logging.error(f"Jadvalni sozlashda xatolik: {str(e)}")
            return {}

    def get_schedule_constraints(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Jadval cheklovlarini qaytarish funksiyasi.

        Returns:
            Jadval cheklovlarining ro'yxati
        """
        return self.schedule_constraints

    def set_schedule_constraints(self, schedule_constraints: Dict[str, List[Tuple[str, str]]]) -> None:
        """
        Jadval cheklovlarini o'rnatish funksiyasi.

        Args:
            schedule_constraints: Jadval cheklovlarining yangi ro'yxati
        """
        self.schedule_constraints = schedule_constraints

    def add_custom_class(self, class_name, subjects):
        """1-4 sinflar uchun yangi sinf qo'shish."""
        self.custom_classes[class_name] = subjects
        logging.info(f"Maxsus sinf {class_name} qo'shildi: {subjects}")

    def assign_teacher_to_class(self, teacher_name, class_name):
        """Sinfga o'qituvchini biriktirish."""
        self.teachers[teacher_name] = class_name
        logging.info(f"O'qituvchi {teacher_name} {class_name} sinfiga biriktirildi.")

# Jadval ko'rish uchun grafik interfeys
class ScheduleView(QMainWindow):
    def __init__(self):
        """
        Jadval ko'rish uchun grafik interfeysni boshlang'ich holatda ishga tushiradi.
        Barcha kerakli elementlarni yaratadi va joylashtiradi.
        """
        super().__init__()
        self.setWindowTitle("Dars Jadvali")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Progress bar - amallar holatini ko'rsatish uchun
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.main_layout.addWidget(self.progress_bar)

        # Sinf qo'shish uchun panel (5-11 sinflar)
        self.class_frame = QWidget()
        self.class_layout = QHBoxLayout(self.class_frame)

        self.class_entry = QLineEdit()
        self.class_entry.setPlaceholderText("Sinf nomi (masalan, 7a)")
        self.class_layout.addWidget(self.class_entry)

        self.class_size_entry = QLineEdit()
        self.class_size_entry.setPlaceholderText("Sinf hajmi (son)")
        self.class_layout.addWidget(self.class_size_entry)

        self.add_class_button = QPushButton("Sinf Qo'shish")
        self.class_layout.addWidget(self.add_class_button)
        self.main_layout.addWidget(self.class_frame)

        # Xona qo'shish uchun panel
        self.room_frame = QWidget()
        self.room_layout = QHBoxLayout(self.room_frame)

        self.room_entry = QLineEdit()
        self.room_entry.setPlaceholderText("Xona ID (masalan, 201)")
        self.room_layout.addWidget(self.room_entry)

        self.room_capacity_entry = QLineEdit()
        self.room_capacity_entry.setPlaceholderText("Xona sig'imi (son)")
        self.room_layout.addWidget(self.room_capacity_entry)

        self.subject_combo = QComboBox()
        self.subject_combo.addItem("Matematika")
        self.subject_combo.addItem("Fizika")
        self.subject_combo.addItem("Ona tili")
        self.subject_combo.addItem("Adabiyot")
        self.subject_combo.addItem("Rus tili")
        self.subject_combo.addItem("Ingliz tili")
        self.subject_combo.addItem("Tabiyat fani")
        self.subject_combo.addItem("Tarix")
        self.subject_combo.addItem("Rasm")
        self.subject_combo.addItem("Kimyo")
        self.subject_combo.addItem("Giyografiya")
        self.subject_combo.addItem("Biyologiya")
        self.subject_combo.addItem("Texnologiya")
        self.subject_combo.addItem("Jismoniy tarbiya")
        self.subject_combo.addItem("Informatika")
        self.subject_combo.addItem("Tarbiya")
        self.subject_combo.addItem("Musiqa")
        self.subject_combo.addItem("Jahon tarixi")
        self.subject_combo.addItem("O'zbekiston tarixi")
        self.subject_combo.addItem("Algebra")
        self.subject_combo.addItem("Geometriya")
        self.subject_combo.addItem("Chizmachilik")
        self.subject_combo.addItem("Huquq")
        self.subject_combo.addItem("Astronomiya")
        self.subject_combo.addItem("Ch.Q.B.T")
        self.room_layout.addWidget(self.subject_combo)

        self.add_room_button = QPushButton("Xona Qo'shish")
        self.room_layout.addWidget(self.add_room_button)
        self.main_layout.addWidget(self.room_frame)

        # 1-4 sinflar uchun panel
        self.custom_class_frame = QWidget()
        self.custom_class_layout = QVBoxLayout(self.custom_class_frame)

        self.custom_class_entry = QLineEdit()
        self.custom_class_entry.setPlaceholderText("Sinf nomi (masalan, 1a)")
        self.custom_class_layout.addWidget(self.custom_class_entry)

        self.custom_subjects_entry = QLineEdit()
        self.custom_subjects_entry.setPlaceholderText("Fanlar (Ona tili:3,Matematika:4)")
        self.custom_class_layout.addWidget(self.custom_subjects_entry)

        self.add_custom_class_button = QPushButton("Maxsus sinf qo'shish")
        self.custom_class_layout.addWidget(self.add_custom_class_button)
        self.main_layout.addWidget(self.custom_class_frame)

        # O'qituvchilar uchun panel
        self.teacher_frame = QWidget()
        self.teacher_layout = QVBoxLayout(self.teacher_frame)

        self.teacher_name_entry = QLineEdit()
        self.teacher_name_entry.setPlaceholderText("O'qituvchi ismi")
        self.teacher_layout.addWidget(self.teacher_name_entry)

        self.teacher_class_entry = QLineEdit()
        self.teacher_class_entry.setPlaceholderText("Sinf nomi (masalan, 1a)")
        self.teacher_layout.addWidget(self.teacher_class_entry)

        self.add_teacher_button = QPushButton("O'qituvchi biriktirish")
        self.teacher_layout.addWidget(self.add_teacher_button)
        self.main_layout.addWidget(self.teacher_frame)

        # Jadval cheklovlarini qo'shish uchun tugma
        self.schedule_constraints_button = QPushButton("Jadvalga talab qo'yish")
        self.main_layout.addWidget(self.schedule_constraints_button)

        # Sinflar ro'yxati uchun widget (5-11 sinflar)
        self.class_list = QListWidget()
        self.class_list.setWindowTitle("5-11 Sinf Ro'yxati")
        self.main_layout.addWidget(self.class_list)

        # 1-4 sinflar ro'yxati
        self.custom_class_list = QListWidget()
        self.custom_class_list.setWindowTitle("1-4 Maxsus sinflar")
        self.main_layout.addWidget(self.custom_class_list)

        # O'qituvchilar ro'yxati
        self.teacher_list = QListWidget()
        self.teacher_list.setWindowTitle("O'qituvchilar")
        self.main_layout.addWidget(self.teacher_list)

        # Fanlar ro'yxati uchun
        self.subject_list = QListWidget()
        self.subject_list.setWindowTitle("Fanlar Ro'yxati")
        self.main_layout.addWidget(self.subject_list)

        # Xonalar ro'yxati uchun
        self.room_list = QListWidget()
        self.room_list.setWindowTitle("Xonalar Ro'yxati")
        self.main_layout.addWidget(self.room_list)

        # Jadval yaratish va saqlash tugmalari
        self.button_frame = QWidget()
        self.button_layout = QHBoxLayout(self.button_frame)

        self.generate_button = QPushButton("Jadval Tuzish")
        self.button_layout.addWidget(self.generate_button)

        self.save_button = QPushButton("Excelga Saqlash")
        self.button_layout.addWidget(self.save_button)
        self.main_layout.addWidget(self.button_frame)

        # Jadval matnini ko'rsatish uchun maydon
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.main_layout.addWidget(self.text_output)

# Worker sinf signal va slotlari
class WorkerSignals(QObject):
    """
    Worker sinf uchun signal lar.
    Jadval yaratish jarayonida xabarlar yuborish uchun ishlatiladi.
    """
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)

# Jadval yaratish uchun ishchi sinf
class ScheduleWorker(QRunnable):
    """
    Jadval yaratish uchun ishchi sinf.
    Thread da ishlaydi va jadvalni avtomatik ravishda yaratadi.
    """
    def __init__(self, model: ScheduleModel):
        super().__init__()
        self.model = model
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """
        Jadval yaratish jarayoni.
        Xatoliklar bo'lsa, signal orqali xabar beradi.
        """
        try:
            class_subjects = self.model.assign_subjects_to_classes(self.model.user_classes)
            weekly_schedule = self.model.create_weekly_schedule(class_subjects)
            self.signals.result.emit(weekly_schedule)
        except Exception as e:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
            logging.error(f"Ishchi threadda xatolik: {e}, {traceback.format_exc()}")  # Batafsil log
            self.signals.finished.emit() # Tugash signalini emit qilishni unutmang
        finally:
            self.signals.finished.emit()

# Jadval boshqaruvchisi
class ScheduleController:
    """
    Jadval boshqaruvchisi.
    Model, View va Worker sinflarini boshqaradi.
    """
    def __init__(self):
        self.model = ScheduleModel()
        self.view = ScheduleView()
        self.setup_signals()
        self.operation_in_progress = False
        logging.basicConfig(level=logging.INFO)
        self.threadpool = QThreadPool()
        logging.info(f"Thread pool: {self.threadpool.maxThreadCount()} threadgacha ishlay oladi")
        self.update_lists()  # Boshlang'ich yuklash

    def setup_signals(self):
        """
        Signal-slotlarni ulash funksiyasi.
        Barcha tugma bosishlar va boshqa hodisalar uchun signal-slotlarni sozlaydi.
        """
        self.view.add_class_button.clicked.connect(self.add_class)
        self.view.add_room_button.clicked.connect(self.add_class_room)
        self.view.schedule_constraints_button.clicked.connect(self.add_schedule_constraints)
        self.view.generate_button.clicked.connect(self.generate_schedule_async)
        self.view.add_custom_class_button.clicked.connect(self.add_custom_class)
        self.view.add_teacher_button.clicked.connect(self.assign_teacher_to_class)

        try:
            self.view.save_button.clicked.connect(self.save_to_excel)
            print("save_to_excel signal muvaffaqiyatli ulandi")
        except AttributeError as e:
            print(f"Xatolik: {str(e)}")
            print("Ehtimol save_to_excel metodi yo'q")

    def add_schedule_constraints(self):
        """
        Jadval cheklovlarini qo'shish funksiyasi.
        Hozircha bo'sh, kelajakda rivojlantiriladi.
        """
        logging.info("Jadval Sozlash Cheklovlari Kiritiladi")
        constraints = defaultdict(list)
        self.model.set_schedule_constraints(constraints)

    def add_class(self):
        """
        Sinf qo'shish funksiyasi (5-11 sinflar).
        Sinf nomi va hajmini tekshirib, modelga qo'shadi.
        """
        class_name = self.view.class_entry.text().strip()
        class_size = self.view.class_size_entry.text().strip()
        try:
            size = int(class_size)
            self.model.add_class(class_name, size)
            self.view.class_list.addItem(f"{class_name} ({size} o'quvchi)")
            self.view.class_entry.clear()
            self.view.class_size_entry.clear()
            self.update_lists()
        except ValueError as e:
            QMessageBox.warning(self.view, "Xatolik", str(e))
            logging.error(f"Sinf qo'shishda xatolik: {str(e)}")

    def add_class_room(self):
        """
        Xona qo'shish funksiyasi.
        Xona raqami va sig'imini tekshirib, modelga qo'shadi.
        """
        room_id = self.view.room_entry.text().strip()
        room_capacity = self.view.room_capacity_entry.text().strip()
        subject = self.view.subject_combo.currentText() # Tanlangan fanni olish
        try:
            capacity = int(room_capacity)
            self.model.add_class_room(room_id, capacity, subject)
            self.view.room_entry.clear()
            self.view.room_capacity_entry.clear()
            self.update_lists()
        except ValueError as e:
            QMessageBox.warning(self.view, "Xatolik", str(e))
            logging.error(f"Xona qo'shishda xatolik: {str(e)}")

    def generate_schedule_async(self):
        """
        Jadvalni avtomatik ravishda yaratish funksiyasi.
        Thread da ishlaydi va progress bar orqali holatni ko'rsatadi.
        """
        if self.operation_in_progress:
            QMessageBox.warning(self.view, "Diqqat!", "Oldingi operatsiya hali tugallanmagan!")
            return

        self.operation_in_progress = True
        logging.info("Jadval yaratish jarayoni boshlandi...") # Loglash

        try:
            self.view.progress_bar.setRange(0, 0)
            worker = ScheduleWorker(self.model)

            def on_error(error_tuple):
                exctype, value, tb = error_tuple
                error_msg = f"Xatolik: {value}\\n{tb}"
                logging.error(error_msg)
                self.handle_error(error_msg)

            worker.signals.error.connect(on_error)
            worker.signals.result.connect(self.on_schedule_completed)
            worker.signals.finished.connect(self.on_schedule_finished)
            #worker.signals.finished.connect(lambda: logging.info("Jadval yaratish jarayoni tugallandi."))

            QThreadPool.globalInstance().start(worker)
        except Exception as e:
            logging.error(f"Jadval yaratishda xatolik: {str(e)}")
            self.handle_error(f"Jadval yaratishda xatolik: {str(e)}")

    def handle_error(self, error_message):
        """
        Xatolikni qayta ishlash funksiyasi.
        Xatolik haqida logga yozadi va foydalanuvchiga xabar beradi.
        """
        self.operation_in_progress = False
        self.view.progress_bar.setRange(0, 1)
        self.view.progress_bar.setValue(0)
        QMessageBox.warning(self.view, "Xatolik", error_message)
        logging.error(f"Kontrollerda xatolik: {error_message}")

    def on_schedule_completed(self, schedule):
        """
        Jadval yaratilgandan so'ng chaqiriladigan funksiya.
        Jadvalni ko'rish maydoniga chiqaradi.
        """
        try:
            jadval_matni = json.dumps(schedule, ensure_ascii=False, indent=2)
            self.view.text_output.setText(jadval_matni)
            self.on_schedule_finished()
        except Exception as e:
            self.handle_error(f"Jadvalni ko'rsatishda xatolik: {str(e)}")

    def on_schedule_finished(self):
        """Jadval yaratish tugagandan so'ng chaqiriladigan funksiya."""
        self.operation_in_progress = False
        self.view.progress_bar.setRange(0, 1)
        self.view.progress_bar.setValue(1)
        logging.info("Jadval yaratish jarayoni yakunlandi.") # Loglash

    def save_to_excel(self):
        if self.operation_in_progress:
            QMessageBox.warning(self.view, "Diqqat!", "Iltimos, avval jadval tayyor bo'lishini kuting!")
            return

        logging.info("Excelga saqlash jarayoni boshlandi...") # Loglash

        try:
            class_subjects = self.model.assign_subjects_to_classes(self.model.user_classes)
            weekly_schedule = self.model.create_weekly_schedule(class_subjects)

            # Jadvalni tekshirish va moslashtirish
            max_lessons_per_day = 0
            for schedule in weekly_schedule.values():
                for day_lessons in schedule.values():
                    max_lessons_per_day = max(max_lessons_per_day, len(day_lessons))

            with pd.ExcelWriter(EXCEL_FILENAME) as writer:
                for class_name, schedule in weekly_schedule.items():
                    # Har bir kun uchun darslar ro'yxatini yaratish
                    data = {}
                    for day in DAYS_OF_WEEK:
                        lessons = schedule.get(day, [])
                        # Agar kerak bo'lsa, bo'sh joylarni qo'shish
                        lessons += [''] * (max_lessons_per_day - len(lessons))
                        data[day] = lessons

                    # DataFrame yaratish
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=class_name, index=False)

            QMessageBox.information(self.view, "Muvaffaqiyat", "Jadval Excelga muvaffaqiyatli saqlandi!")
            logging.info("Excelga saqlash jarayoni muvaffaqiyatli yakunlandi.") # Loglash

        except Exception as e:
            self.handle_error(f"Excel fayliga saqlashda xatolik: {str(e)}")
            logging.error(f"Excelga saqlashda xatolik: {str(e)}") # Loglash

    def add_custom_class(self):
        """1-4 sinflar uchun yangi sinf qo'shish."""
        class_name = self.view.custom_class_entry.text().strip()
        subjects_text = self.view.custom_subjects_entry.text().strip()

        try:
            subjects = {}
            for item in subjects_text.split(','):
                subject, hours = item.split(':')
                subjects[subject.strip()] = int(hours.strip())

            self.model.add_custom_class(class_name, subjects)
            self.update_lists()
            self.view.custom_class_entry.clear()
            self.view.custom_subjects_entry.clear()
        except ValueError as e:
            QMessageBox.warning(self.view, "Xatolik", str(e))
            logging.error(f"Maxsus sinf qo'shishda xatolik: {str(e)}")

    def assign_teacher_to_class(self):
        """Sinfga o'qituvchini biriktirish."""
        teacher_name = self.view.teacher_name_entry.text().strip()
        class_name = self.view.teacher_class_entry.text().strip()

        try:
            self.model.assign_teacher_to_class(teacher_name, class_name)
            self.update_lists()
            self.view.teacher_name_entry.clear()
            self.view.teacher_class_entry.clear()
        except ValueError as e:
            QMessageBox.warning(self.view, "Xatolik", str(e))
            logging.error(f"O'qituvchi biriktirishda xatolik: {str(e)}")

    def update_lists(self):
        """UI dagi ro'yxatlarni yangilash."""
        self.view.subject_list.clear()
        self.view.room_list.clear()
        self.view.class_list.clear()  # 5-11 sinflar ro'yxati
        self.view.custom_class_list.clear() # 1-4 sinflar
        self.view.teacher_list.clear() # O'qituvchilar

        # Fanlarni ro'yxatga qo'shish
        for subject in self.model.subject_rooms.keys():
            self.view.subject_list.addItem(subject)

        # Xonalarni ro'yxatga qo'shish
        for room_id, capacity in self.model.class_rooms.items():
            self.view.room_list.addItem(f"{room_id} ({capacity} o'quvchi)")

        # 5-11 sinflarni ro'yxatga qo'shish
        for class_name in self.model.user_classes:
            self.view.class_list.addItem(class_name)

        # 1-4 sinflarni ro'yxatga qo'shish
        for class_name, subjects in self.model.custom_classes.items():
            self.view.custom_class_list.addItem(f"{class_name}: {subjects}")

        # O'qituvchilarni ro'yxatga qo'shish
        for teacher_name, class_name in self.model.teachers.items():
            self.view.teacher_list.addItem(f"{teacher_name}: {class_name}")

# Dasturni boshlash
if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = ScheduleController()
    controller.view.show()
    sys.exit(app.exec())
    print("Dastur muvaffaqiyatli yakunlandi!")
