import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import re
from collections import defaultdict
import json
import math
from datetime import datetime
import os
import openai
import threading
import webbrowser
from html import escape
import random
import networkx as nx
from sklearn.cluster import KMeans
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
import uuid
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import to_hex
from matplotlib.collections import LineCollection


class Person:
    def __init__(self, full_name, birth_date=None, source_file=None):
        self.full_name = self.normalize_name(full_name)
        self.birth_date = birth_date
        self.phones = set()
        self.emails = set()
        self.addresses = set()
        self.passports = set()
        self.cars = set()
        self.accounts = defaultdict(set)
        self.relations = set()
        self.driver_license = None
        self.snils = None
        self.inn = None
        self.jobs = set()
        self.social_media = defaultdict(set)
        self.bank_accounts = set()
        self.orders = []
        self.properties = set()
        self.aliases = set()
        self.source_files = set()
        self.id = str(uuid.uuid4())  # Уникальный идентификатор
        if source_file:
            self.source_files.add(source_file)
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.created_by = "system"
        self.updated_by = "system"

    @staticmethod
    def normalize_name(name):
        """Приводит имя к стандартному формату (Фамилия Имя Отчество)"""
        parts = re.split(r'\s+', name.strip().title())
        if len(parts) >= 3:
            return ' '.join(parts[:3])
        elif len(parts) == 2:
            return f"{parts[0]} {parts[1]} "
        return name.title()

    def add_relation(self, relation_type, related_person, details=None):
        """Добавляет связь с другим человеком"""
        if not details:
            details = {}

        # Преобразуем списки в кортежи для хеширования
        if 'source_files' in details:
            details['source_files'] = tuple(details['source_files'])

        # Добавляем информацию о файле-источнике, если есть
        if self.source_files:
            details['source_files'] = tuple(self.source_files)

        # Добавляем причину связи, если не указана
        if 'reason' not in details:
            if isinstance(related_person, Person) and self.source_files & related_person.source_files:
                details['reason'] = 'из одного файла'
            elif isinstance(related_person, Person):
                details['reason'] = 'одинаковые имена в разных файлах'

        # Создаем неизменяемую версию деталей
        frozen_details = tuple(sorted(details.items()))

        # Проверяем, нет ли уже такой связи
        for rel in self.relations:
            if (rel[0] == relation_type and
                    ((isinstance(related_person, Person) and rel[1].full_name == related_person.full_name) or
                     (not isinstance(related_person, Person) and rel[1] == related_person)) and
                    rel[2] == frozen_details):
                return False

        self.relations.add((relation_type, related_person, frozen_details))
        self.updated_at = datetime.now().isoformat()
        self.updated_by = "user"

        # Добавляем обратную связь
        if isinstance(related_person, Person):
            reverse_relation = self.get_reverse_relation(relation_type)
            related_person.add_relation(reverse_relation, self, details)

        return True

    def remove_relation(self, relation_type, related_person):
        """Удаляет связь с другим человеком"""
        to_remove = []

        for rel in self.relations:
            if (rel[0] == relation_type and
                    ((isinstance(related_person, Person) and rel[1].full_name == related_person.full_name) or
                     (not isinstance(related_person, Person) and rel[1] == related_person))):
                to_remove.append(rel)

        for rel in to_remove:
            self.relations.remove(rel)

        self.updated_at = datetime.now().isoformat()
        self.updated_by = "user"

        # Удаляем обратную связь
        if isinstance(related_person, Person):
            reverse_relation = self.get_reverse_relation(relation_type)
            related_person.remove_relation(reverse_relation, self)

        return len(to_remove) > 0

    @staticmethod
    def get_reverse_relation(relation_type):
        """Возвращает обратный тип связи"""
        reverse_relations = {
            'муж': 'жена',
            'жена': 'муж',
            'отец': 'сын/дочь',
            'мать': 'сын/дочь',
            'сын': 'родитель',
            'дочь': 'родитель',
            'брат': 'брат/сестра',
            'сестра': 'брат/сестра',
            'друг': 'друг',
            'коллега': 'коллега',
            'партнер': 'партнер',
            'связь': 'связь',
            'возможная связь': 'возможная связь'
        }
        return reverse_relations.get(relation_type.lower(), relation_type)

    def merge(self, other_person):
        """Объединяет данные с другим объектом Person"""
        if not isinstance(other_person, Person):
            return False

        # Объединяем данные
        self.phones.update(other_person.phones)
        self.emails.update(other_person.emails)
        self.addresses.update(other_person.addresses)
        self.passports.update(other_person.passports)
        self.cars.update(other_person.cars)
        self.jobs.update(other_person.jobs)
        self.bank_accounts.update(other_person.bank_accounts)
        self.source_files.update(other_person.source_files)
        self.aliases.add(other_person.full_name)
        self.aliases.update(other_person.aliases)
        self.updated_at = datetime.now().isoformat()
        self.updated_by = "user"

        # Объединяем связи (без дубликатов)
        for rel in other_person.relations:
            # Исключаем связи с самим собой
            if isinstance(rel[1], Person) and rel[1] == self:
                continue

            # Проверяем, нет ли уже такой связи
            exists = False
            for my_rel in self.relations:
                if (my_rel[0] == rel[0] and
                        ((isinstance(rel[1], Person) and isinstance(my_rel[1], Person) and
                          my_rel[1].full_name == rel[1].full_name) or
                         (not isinstance(rel[1], Person) and not isinstance(my_rel[1], Person) and
                          my_rel[1] == rel[1]))):
                    exists = True
                    break

            if not exists:
                self.relations.add(rel)

        return True

    def __str__(self):
        return f"{self.full_name} ({self.birth_date or 'дата неизвестна'})"

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'birth_date': self.birth_date,
            'phones': list(self.phones),
            'emails': list(self.emails),
            'addresses': list(self.addresses),
            'passports': list(self.passports),
            'cars': list(self.cars),
            'driver_license': self.driver_license,
            'snils': self.snils,
            'inn': self.inn,
            'jobs': list(self.jobs),
            'social_media': dict(self.social_media),
            'bank_accounts': list(self.bank_accounts),
            'aliases': list(self.aliases),
            'source_files': list(self.source_files),
            'relations': [
                {
                    'type': rel[0],
                    'related_person': rel[1].full_name if isinstance(rel[1], Person) else rel[1],
                    'details': dict(rel[2])  # Преобразуем обратно в словарь
                }
                for rel in self.relations
            ],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }


class DataVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("BastardGraph")
        self.root.geometry("1400x900")

        # Настройки API OpenAI
        self.openai_api_key = None
        self.openai_model = "gpt-3.5-turbo"

        # Настройки геокодера
        self.geolocator = Nominatim(user_agent="data_visualizer")
        self.geocoded_addresses = {}

        # Настройки логгера
        self.setup_logging()

        # Данные
        self.people = {}
        self.current_person = None
        self.graph_objects = []
        self.search_results = []
        self.file_path = None
        self.selected_node = None
        self.node_positions = {}
        self.people_to_merge = set()
        self.people_to_analyze = set()  # Люди для анализа ChatGPT
        self.current_file_people = set()  # Люди из текущего обрабатываемого файла
        self.graph = nx.Graph()  # Граф для анализа связей
        self.clusters = {}  # Кластеры людей
        self.graph_layout = "force_atlas"  # Текущий алгоритм размещения
        self.dark_mode = False  # Режим темной темы
        self.graph_settings = {
            'node_size': 1000,
            'edge_width': 2,
            'central_color': '#a6d8ff',
            'family_color': '#ffb6c1',
            'work_color': '#98fb98',
            'other_color': '#ffd700',
            'highlight_color': '#ff0000',
            'bg_color': '#ffffff',
            'text_color': '#000000'
        }

        # Стили
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Selected.TButton', background='#a6d8ff')

        # Основные фреймы
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Создаем контейнер для левой панели с прокруткой
        self.control_frame_container = ttk.Frame(self.main_frame, width=300)
        self.control_frame_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Canvas и Scrollbar для левой панели
        self.control_canvas = tk.Canvas(self.control_frame_container, highlightthickness=0)
        self.control_scrollbar = ttk.Scrollbar(self.control_frame_container, orient="vertical",
                                               command=self.control_canvas.yview)

        self.control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.control_canvas.configure(yscrollcommand=self.control_scrollbar.set)

        # Фрейм для содержимого левой панели
        self.control_frame = ttk.Frame(self.control_canvas)
        self.control_canvas.create_window((0, 0), window=self.control_frame, anchor="nw")

        # Привязка колесика мыши
        self.control_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Создаем display_frame для правой части
        self.display_frame = ttk.Frame(self.main_frame)
        self.display_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)



        # Элементы управления
        ttk.Label(self.control_frame, text="Управление", style='Title.TLabel').pack(pady=10)

        self.file_frame = ttk.LabelFrame(self.control_frame, text="Файл", padding=10)
        self.file_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(self.file_frame, text="Открыть файл", command=self.open_file).pack(fill=tk.X, pady=2)
        ttk.Button(self.file_frame, text="Открыть папку", command=self.open_folder).pack(fill=tk.X, pady=2)
        ttk.Button(self.file_frame, text="Сохранить данные", command=self.save_data).pack(fill=tk.X, pady=2)
        ttk.Button(self.file_frame, text="Экспорт в JSON", command=self.export_to_json).pack(fill=tk.X, pady=2)
        ttk.Button(self.file_frame, text="Экспорт в HTML", command=self.export_to_html).pack(fill=tk.X, pady=2)
        ttk.Button(self.file_frame, text="Создать резервную копию", command=self.create_backup).pack(fill=tk.X, pady=2)
        ttk.Button(self.file_frame, text="Восстановить из копии", command=self.restore_from_backup).pack(fill=tk.X,
                                                                                                         pady=2)

        self.settings_frame = ttk.LabelFrame(self.control_frame, text="Настройки", padding=10)
        self.settings_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.settings_frame, text="API Key OpenAI:").pack(anchor=tk.W)
        self.api_key_entry = ttk.Entry(self.settings_frame)
        self.api_key_entry.pack(fill=tk.X, pady=2)
        ttk.Button(self.settings_frame, text="Установить ключ", command=self.set_api_key).pack(fill=tk.X, pady=2)

        ttk.Button(self.settings_frame, text="Темная тема", command=self.toggle_dark_mode).pack(fill=tk.X, pady=2)

        self.graph_settings_frame = ttk.LabelFrame(self.control_frame, text="Настройки графа", padding=10)
        self.graph_settings_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.graph_settings_frame, text="Алгоритм размещения:").pack(anchor=tk.W)
        self.layout_var = tk.StringVar(value="force_atlas")
        ttk.Radiobutton(self.graph_settings_frame, text="Force Atlas", variable=self.layout_var,
                        value="force_atlas", command=self.update_graph_layout).pack(anchor=tk.W)
        ttk.Radiobutton(self.graph_settings_frame, text="Fruchterman-Reingold", variable=self.layout_var,
                        value="fruchterman", command=self.update_graph_layout).pack(anchor=tk.W)
        ttk.Radiobutton(self.graph_settings_frame, text="Circular", variable=self.layout_var,
                        value="circular", command=self.update_graph_layout).pack(anchor=tk.W)

        ttk.Label(self.graph_settings_frame, text="Размер узлов:").pack(anchor=tk.W)
        self.node_size_scale = ttk.Scale(self.graph_settings_frame, from_=500, to=2000,
                                         command=lambda v: self.update_graph_style('node_size', int(float(v))))
        self.node_size_scale.set(self.graph_settings['node_size'])
        self.node_size_scale.pack(fill=tk.X, pady=2)

        ttk.Label(self.graph_settings_frame, text="Толщина связей:").pack(anchor=tk.W)
        self.edge_width_scale = ttk.Scale(self.graph_settings_frame, from_=1, to=5,
                                          command=lambda v: self.update_graph_style('edge_width', float(v)))
        self.edge_width_scale.set(self.graph_settings['edge_width'])
        self.edge_width_scale.pack(fill=tk.X, pady=2)

        self.search_frame = ttk.LabelFrame(self.control_frame, text="Поиск", padding=10)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)

        self.search_entry = ttk.Entry(self.search_frame)
        self.search_entry.pack(fill=tk.X, pady=2)
        self.search_entry.bind('<Return>', lambda e: self.search_data())

        ttk.Button(self.search_frame, text="Искать", command=self.search_data).pack(fill=tk.X, pady=2)
        ttk.Button(self.search_frame, text="Сброс поиска", command=self.reset_search).pack(fill=tk.X, pady=2)
        ttk.Button(self.search_frame, text="Найти кратчайший путь", command=self.find_shortest_path).pack(fill=tk.X,
                                                                                                          pady=2)

        self.filter_frame = ttk.LabelFrame(self.control_frame, text="Фильтры", padding=10)
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.filter_frame, text="Сортировка:").pack(anchor=tk.W)
        self.sort_var = tk.StringVar(value="name")
        ttk.Combobox(self.filter_frame, textvariable=self.sort_var,
                     values=["по имени", "по дате рождения", "по количеству связей"]).pack(fill=tk.X, pady=2)

        ttk.Label(self.filter_frame, text="Группировка:").pack(anchor=tk.W)
        self.group_var = tk.StringVar(value="none")
        ttk.Combobox(self.filter_frame, textvariable=self.group_var,
                     values=["без группировки", "по кластерам", "по категориям"]).pack(fill=tk.X, pady=2)

        ttk.Button(self.filter_frame, text="Применить фильтры", command=self.apply_filters).pack(fill=tk.X, pady=2)

        self.people_frame = ttk.LabelFrame(self.control_frame, text="Люди", padding=10)
        self.people_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.people_listbox = tk.Listbox(self.people_frame, height=20, selectmode=tk.EXTENDED)
        self.people_listbox.pack(fill=tk.BOTH, expand=True, pady=2)
        self.people_listbox.bind('<<ListboxSelect>>', self.on_person_select)
        self.people_listbox.bind('<Button-3>', self.show_people_list_menu)

        self.action_frame = ttk.Frame(self.control_frame)
        self.action_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(self.action_frame, text="Показать связи", command=self.show_relations).pack(side=tk.LEFT,
                                                                                               expand=True, padx=2)
        ttk.Button(self.action_frame, text="Очистить", command=self.clear_canvas).pack(side=tk.LEFT, expand=True,
                                                                                       padx=2)
        ttk.Button(self.action_frame, text="Анализ ChatGPT", command=self.analyze_with_chatgpt).pack(side=tk.LEFT,
                                                                                                     expand=True,
                                                                                                     padx=2)
        ttk.Button(self.action_frame, text="Статистика", command=self.show_statistics).pack(side=tk.LEFT, expand=True,
                                                                                            padx=2)

        # Холст для отображения
        self.canvas_frame = ttk.Frame(self.display_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # Контекстное меню для графа
        self.graph_menu = tk.Menu(self.root, tearoff=0)
        self.graph_menu.add_command(label="Добавить связь", command=self.add_relation_dialog)
        self.graph_menu.add_command(label="Удалить связь", command=self.remove_relation_dialog)
        self.graph_menu.add_separator()
        self.graph_menu.add_command(label="Добавить в объединение", command=self.add_to_merge_list)
        self.graph_menu.add_command(label="Добавить в анализ", command=self.add_to_analysis_list)
        self.graph_menu.add_separator()
        self.graph_menu.add_command(label="Объединить выбранных", command=self.merge_selected_people)
        self.graph_menu.add_command(label="Удалить человека", command=self.delete_selected_person)
        self.graph_menu.add_command(label="Показать информацию", command=self.show_selected_node_info)
        self.graph_menu.add_command(label="Показать связи 2-го уровня", command=self.show_second_level_relations)
        self.graph_menu.add_command(label="Найти кратчайший путь", command=self.find_shortest_path_from_menu)

        # Контекстное меню для списка людей
        self.people_list_menu = tk.Menu(self.root, tearoff=0)
        self.people_list_menu.add_command(label="Добавить связь", command=self.add_relation_from_list)
        self.people_list_menu.add_command(label="Удалить связь", command=self.remove_relation_from_list)
        self.people_list_menu.add_separator()
        self.people_list_menu.add_command(label="Добавить в объединение", command=self.add_to_merge_list_from_list)
        self.people_list_menu.add_command(label="Добавить в анализ", command=self.add_to_analysis_list_from_list)
        self.people_list_menu.add_separator()
        self.people_list_menu.add_command(label="Объединить выбранных", command=self.merge_selected_people)
        self.people_list_menu.add_command(label="Удалить человека", command=self.delete_selected_person_from_list)
        self.people_list_menu.add_command(label="Показать информацию", command=self.show_selected_list_person_info)
        self.people_list_menu.add_command(label="Показать на карте", command=self.show_on_map_from_list)

        # Полосы прокрутки
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Внутренний фрейм для элементов
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Статус бар
        self.status_bar = ttk.Label(self.display_frame, text="Готов к работе", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)



        # Переменные для панорамирования и масштабирования
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.zoom_level = 1.0

        self.pan_start_x = 0
        self.pan_start_y = 0
        self.zoom_level = 1.0
        self.last_zoom_center = (0, 0)

        # Настройка прокрутки
        self.setup_scrollbars()

    def _on_mousewheel(self, event):
        """Обработчик прокрутки колесиком мыши"""
        if event.num == 4 or event.delta > 0:
            self.control_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.control_canvas.yview_scroll(1, "units")

    def setup_scrollbars(self):
        """Обновляем конфигурацию скроллбара после добавления всех виджетов"""
        self.control_frame.update_idletasks()
        self.control_canvas.config(scrollregion=self.control_canvas.bbox("all"))

    def start_pan(self, event):
        """Начало панорамирования"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.scan_mark(event.x, event.y)


    def pan(self, event):
        """Панорамирование графа"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)


    def zoom(self, event):
        """Масштабирование графа с центром на курсоре мыши"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_level *= factor

        # Сохраняем центр масштабирования
        self.last_zoom_center = (x, y)

        self.canvas.scale("all", x, y, factor, factor)

        # Обновляем позиции узлов после масштабирования
        for node_id, (node_x, node_y) in self.node_positions.items():
            scaled_x = x + (node_x - x) * factor
            scaled_y = y + (node_y - y) * factor
            self.node_positions[node_id] = (scaled_x, scaled_y)


    def reset_zoom(self, event=None):
        """Сброс масштабирования с анимацией"""
        if not hasattr(self, 'node_positions') or not self.node_positions:
            return

        # Находим центр графа
        all_x = [pos[0] for pos in self.node_positions.values()]
        all_y = [pos[1] for pos in self.node_positions.values()]
        center_x = sum(all_x) / len(all_x)
        center_y = sum(all_y) / len(all_y)

        # Вычисляем текущий масштаб
        current_scale = self.canvas.scale("all", 0, 0, 0, 0)[0]

        if current_scale == 1.0:
            return

        # Плавное возвращение к масштабу 1.0
        steps = 10
        step_factor = (1.0 / current_scale) ** (1.0 / steps)

        for _ in range(steps):
            self.canvas.scale("all", center_x, center_y, step_factor, step_factor)
            self.canvas.update()
            time.sleep(0.03)

        self.zoom_level = 1.0

        # Обновляем позиции узлов
        for node_id in self.node_positions:
            x, y = self.node_positions[node_id]
            scaled_x = center_x + (x - center_x) * (1.0 / current_scale)
            scaled_y = center_y + (y - center_y) * (1.0 / current_scale)
            self.node_positions[node_id] = (scaled_x, scaled_y)


    def setup_bindings(self):
        """Настройка привязок клавиш и мыши"""
        # Привязка правой кнопки мыши
        self.canvas.bind("<Button-3>", self.show_graph_menu)
        self.canvas.bind("<Motion>", self.highlight_connected_nodes)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-2>", self.reset_zoom)  # Для Linux, кнопка 2 - средняя кнопка мыши
        self.canvas.bind("<Button-3>", self.reset_zoom, add='+')  # Для Windows, правой кнопкой с Ctrl
        self.canvas.bind("<Control-Button-1>", self.reset_zoom)

        # Горячие клавиши
        self.root.bind("<Control-plus>", lambda e: self.zoom_with_key(1.1))
        self.root.bind("<Control-minus>", lambda e: self.zoom_with_key(0.9))
        self.root.bind("<Control-0>", self.reset_zoom)


    def zoom_with_key(self, factor):
        """Масштабирование с помощью клавиш"""
        if not hasattr(self, 'last_zoom_center') or not self.last_zoom_center:
            center_x = self.canvas.winfo_width() / 2
            center_y = self.canvas.winfo_height() / 2
        else:
            center_x, center_y = self.last_zoom_center

        self.zoom_level *= factor
        self.canvas.scale("all", center_x, center_y, factor, factor)

        # Обновляем позиции узлов
        for node_id in self.node_positions:
            x, y = self.node_positions[node_id]
            scaled_x = center_x + (x - center_x) * factor
            scaled_y = center_y + (y - center_y) * factor
            self.node_positions[node_id] = (scaled_x, scaled_y)

    def add_relation_dialog(self):
        """Диалог добавления новой связи"""
        if not self.selected_node or not self.current_person:
            return

        # Находим выбранного человека
        related_person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                related_person = p
                break

        if not related_person or related_person == self.current_person:
            return

        # Диалог для ввода типа связи
        relation_type = simpledialog.askstring(
            "Добавить связь",
            f"Введите тип связи между {self.current_person.full_name} и {related_person.full_name}:",
            parent=self.root
        )

        if relation_type:
            # Добавляем информацию о файлах-источниках
            details = {}
            if self.current_person.source_files:
                details['source_files'] = list(self.current_person.source_files)
            if related_person.source_files:
                if 'source_files' in details:
                    details['source_files'].extend(list(related_person.source_files))
                else:
                    details['source_files'] = list(related_person.source_files)

            # Убираем дубликаты
            if 'source_files' in details:
                details['source_files'] = list(set(details['source_files']))

            # Добавляем причину связи
            if self.current_person.source_files & related_person.source_files:
                details['reason'] = 'из одного файла'
            else:
                details['reason'] = 'вручную добавленная связь'

            if self.current_person.add_relation(relation_type, related_person, details):
                self.show_relations()
                messagebox.showinfo("Успех", "Связь успешно добавлена")
                self.log_action("Добавление связи",
                              f"{self.current_person.full_name} -> {related_person.full_name}: {relation_type}")
            else:
                messagebox.showinfo("Информация", "Такая связь уже существует")

    def setup_logging(self):
        """Настройка системы логирования"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        self.logger = logging.getLogger("DataVisualizer")
        self.logger.setLevel(logging.INFO)

        # Ротация логов - 5 файлов по 1MB каждый
        handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_action(self, action, details):
        """Логирование действий пользователя"""
        self.logger.info(f"{action}: {details}")

    def toggle_dark_mode(self):
        """Переключение темной темы"""
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.style.configure('TFrame', background='#333333')
            self.style.configure('TLabel', background='#333333', foreground='white')
            self.style.configure('TButton', background='#555555', foreground='white')
            self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'), foreground='white')
            self.canvas.configure(bg='#222222')
            self.graph_settings['bg_color'] = '#222222'
            self.graph_settings['text_color'] = '#ffffff'
        else:
            self.style.configure('TFrame', background='#f0f0f0')
            self.style.configure('TLabel', background='#f0f0f0', foreground='black')
            self.style.configure('TButton', background='#f0f0f0', foreground='black')
            self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'), foreground='black')
            self.canvas.configure(bg='white')
            self.graph_settings['bg_color'] = '#ffffff'
            self.graph_settings['text_color'] = '#000000'

        # Перерисовываем граф, если он есть
        if self.current_person:
            self.show_relations()

    def update_graph_layout(self):
        """Обновляет алгоритм размещения графа"""
        self.graph_layout = self.layout_var.get()
        if self.current_person:
            self.show_relations()

    def update_graph_style(self, setting, value):
        """Обновляет настройки отображения графа"""
        self.graph_settings[setting] = value
        if self.current_person:
            self.show_relations()

    def highlight_connected_nodes(self, event):
        """Подсветка связанных узлов при наведении"""
        if not self.current_person or not hasattr(self, 'graph'):
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        hovered_node = None

        # Находим узел, над которым находится курсор
        for node_id, (node_x, node_y) in self.node_positions.items():
            if (node_x - 60 <= x <= node_x + 60 and
                    node_y - 40 <= y <= node_y + 40):
                hovered_node = node_id
                break

        if hovered_node:
            # Находим все связанные узлы
            connected_nodes = set()
            for rel in self.current_person.relations:
                if isinstance(rel[1], Person):
                    node_id = f"node_{rel[1].full_name}"
                    connected_nodes.add(node_id)

            # Подсвечиваем связанные узлы
            for node_id in self.node_positions:
                if node_id == hovered_node:
                    self.canvas.itemconfig(node_id, fill=self.graph_settings['highlight_color'])
                elif node_id in connected_nodes:
                    self.canvas.itemconfig(node_id, fill="#ffff00")  # Желтый для связанных узлов
                else:
                    # Возвращаем исходный цвет
                    if 'семь' in node_id.lower() or 'супруг' in node_id.lower():
                        self.canvas.itemconfig(node_id, fill=self.graph_settings['family_color'])
                    elif 'работ' in node_id.lower() or 'коллег' in node_id.lower():
                        self.canvas.itemconfig(node_id, fill=self.graph_settings['work_color'])
                    elif 'возможн' in node_id.lower():
                        self.canvas.itemconfig(node_id, fill="#ffa07a")
                    else:
                        self.canvas.itemconfig(node_id, fill=self.graph_settings['other_color'])

    def show_second_level_relations(self):
        """Показывает связи второго уровня (через промежуточных людей)"""
        if not self.selected_node or not self.current_person:
            return

        # Находим выбранного человека
        related_person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                related_person = p
                break

        if not related_person or related_person == self.current_person:
            return

        # Строим граф всех связей
        self.build_relation_graph()

        # Находим все пути между текущим и выбранным человеком
        try:
            paths = list(nx.all_simple_paths(self.graph, self.current_person.id, related_person.id, cutoff=3))
        except nx.NetworkXNoPath:
            messagebox.showinfo("Информация", "Нет связей между выбранными людьми")
            return

        # Собираем всех людей, участвующих в связях
        people_in_paths = set()
        for path in paths:
            for person_id in path:
                people_in_paths.add(person_id)

        # Показываем только этих людей и их связи
        self.show_filtered_relations(people_in_paths)

    def build_relation_graph(self):
        """Строит граф всех связей между людьми"""
        self.graph.clear()

        # Добавляем всех людей как узлы
        for person in self.people.values():
            self.graph.add_node(person.id, name=person.full_name, person=person)

        # Добавляем связи между людьми
        for person in self.people.values():
            for rel_type, related_person, details in person.relations:
                if isinstance(related_person, Person):
                    self.graph.add_edge(person.id, related_person.id, type=rel_type, details=dict(details))

    def show_filtered_relations(self, person_ids):
        """Показывает связи только между выбранными людьми"""
        self.clear_canvas()
        self.node_positions = {}

        # Создаем холст для графа
        graph_canvas = tk.Canvas(self.inner_frame, width=1000, height=700, bg=self.graph_settings['bg_color'])
        graph_canvas.grid(row=0, column=0, sticky="nsew")
        self.graph_objects.append(graph_canvas)

        # Получаем список людей для отображения
        people_to_show = [p for p in self.people.values() if p.id in person_ids]
        if not people_to_show:
            graph_canvas.create_text(500, 350, text="Нет данных для отображения",
                                     font=('Arial', 12), fill=self.graph_settings['text_color'])
            return

        # Создаем подграф для этих людей
        subgraph = self.graph.subgraph(person_ids)

        # Выбираем алгоритм размещения
        if self.graph_layout == "force_atlas":
            pos = nx.spring_layout(subgraph, k=0.5, iterations=50)
        elif self.graph_layout == "fruchterman":
            pos = nx.fruchterman_reingold_layout(subgraph, k=0.5)
        else:  # circular
            pos = nx.circular_layout(subgraph)

        # Масштабируем координаты для отображения на холсте
        min_x = min(v[0] for v in pos.values())
        max_x = max(v[0] for v in pos.values())
        min_y = min(v[1] for v in pos.values())
        max_y = max(v[1] for v in pos.values())

        scale_x = 800 / (max_x - min_x) if max_x != min_x else 1
        scale_y = 600 / (max_y - min_y) if max_y != min_y else 1
        scale = min(scale_x, scale_y) * 0.8

        center_x = (max_x + min_x) / 2
        center_y = (max_y + min_y) / 2

        # Рисуем узлы и связи
        for node, (x, y) in pos.items():
            person = next((p for p in self.people.values() if p.id == node), None)
            if not person:
                continue

            # Преобразуем координаты
            canvas_x = 500 + (x - center_x) * scale * 500
            canvas_y = 350 + (y - center_y) * scale * 350

            node_id = f"node_{person.full_name}"
            self.node_positions[node_id] = (canvas_x, canvas_y)

            # Цвет узла в зависимости от типа связей
            node_color = self.graph_settings['other_color']
            if person == self.current_person:
                node_color = self.graph_settings['central_color']
            else:
                for rel in self.current_person.relations:
                    if isinstance(rel[1], Person) and rel[1].id == person.id:
                        if 'семь' in rel[0].lower() or 'супруг' in rel[0].lower():
                            node_color = self.graph_settings['family_color']
                        elif 'работ' in rel[0].lower() or 'коллег' in rel[0].lower():
                            node_color = self.graph_settings['work_color']
                        break

            # Рисуем узел
            graph_canvas.create_oval(
                canvas_x - 60, canvas_y - 40, canvas_x + 60, canvas_y + 40,
                fill=node_color, outline='#8b4513', tags=node_id
            )

            # Имя человека (только фамилия)
            last_name = person.full_name.split()[0] if ' ' in person.full_name else person.full_name
            graph_canvas.create_text(
                canvas_x, canvas_y, text=last_name,
                font=('Arial', 10, 'bold'), fill='#8b4513', tags=node_id
            )

        # Рисуем связи
        for edge in subgraph.edges(data=True):
            source_person = next((p for p in self.people.values() if p.id == edge[0]), None)
            target_person = next((p for p in self.people.values() if p.id == edge[1]), None)
            if not source_person or not target_person:
                continue

            source_node = f"node_{source_person.full_name}"
            target_node = f"node_{target_person.full_name}"
            if source_node not in self.node_positions or target_node not in self.node_positions:
                continue

            x1, y1 = self.node_positions[source_node]
            x2, y2 = self.node_positions[target_node]

            # Рисуем линию связи
            graph_canvas.create_line(
                x1, y1, x2, y2,
                arrow=tk.LAST, fill='#666666', width=self.graph_settings['edge_width']
            )

            # Подпись связи (посередине линии)
            rel_type = edge[2].get('type', 'связь')
            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2

            graph_canvas.create_text(
                label_x, label_y, text=rel_type,
                font=('Arial', 8), fill=self.graph_settings['text_color']
            )

    def find_shortest_path(self):
        """Находит кратчайший путь между двумя людьми"""
        if len(self.people_listbox.curselection()) != 2:
            messagebox.showwarning("Предупреждение", "Выберите ровно двух человек для поиска пути")
            return

        person1_str = self.people_listbox.get(self.people_listbox.curselection()[0])
        person2_str = self.people_listbox.get(self.people_listbox.curselection()[1])

        person1 = None
        person2 = None

        # Находим объекты выбранных людей
        for person in self.people.values():
            if str(person) == person1_str:
                person1 = person
            if str(person) == person2_str:
                person2 = person
            if person1 and person2:
                break

        if not person1 or not person2:
            messagebox.showerror("Ошибка", "Не удалось найти выбранных людей")
            return

        # Строим граф всех связей
        self.build_relation_graph()

        # Ищем кратчайший путь
        try:
            path = nx.shortest_path(self.graph, person1.id, person2.id)
        except nx.NetworkXNoPath:
            messagebox.showinfo("Информация", "Нет пути между выбранными людьми")
            return

        # Получаем людей на пути
        people_in_path = [next(p for p in self.people.values() if p.id == node_id) for node_id in path]

        # Показываем путь
        self.show_shortest_path(people_in_path)

    def find_shortest_path_from_menu(self):
        """Находит кратчайший путь между текущим и выбранным человеком из меню"""
        if not self.selected_node or not self.current_person:
            return

        # Находим выбранного человека
        related_person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                related_person = p
                break

        if not related_person or related_person == self.current_person:
            return

        # Строим граф всех связей
        self.build_relation_graph()

        # Ищем кратчайший путь
        try:
            path = nx.shortest_path(self.graph, self.current_person.id, related_person.id)
        except nx.NetworkXNoPath:
            messagebox.showinfo("Информация", "Нет пути между выбранными людьми")
            return

        # Получаем людей на пути
        people_in_path = [next(p for p in self.people.values() if p.id == node_id) for node_id in path]

        # Показываем путь
        self.show_shortest_path(people_in_path)

    def show_shortest_path(self, people_in_path):
        """Показывает кратчайший путь между людьми"""
        self.clear_canvas()
        self.node_positions = {}

        # Создаем холст для графа
        graph_canvas = tk.Canvas(self.inner_frame, width=1000, height=700, bg=self.graph_settings['bg_color'])
        graph_canvas.grid(row=0, column=0, sticky="nsew")
        self.graph_objects.append(graph_canvas)

        if len(people_in_path) < 2:
            graph_canvas.create_text(500, 350, text="Нет данных для отображения",
                                     font=('Arial', 12), fill=self.graph_settings['text_color'])
            return

        # Располагаем людей по кругу
        angle_step = 360 / len(people_in_path)
        center_x, center_y = 500, 350
        radius = 250

        for i, person in enumerate(people_in_path):
            angle = math.radians(i * angle_step)
            node_x = center_x + radius * math.cos(angle)
            node_y = center_y + radius * math.sin(angle)

            node_id = f"node_{person.full_name}"
            self.node_positions[node_id] = (node_x, node_y)

            # Цвет узла - красный для выделения пути
            graph_canvas.create_oval(
                node_x - 60, node_y - 40, node_x + 60, node_y + 40,
                fill='#ff0000', outline='#8b4513', tags=node_id
            )

            # Имя человека (только фамилия)
            last_name = person.full_name.split()[0] if ' ' in person.full_name else person.full_name
            graph_canvas.create_text(
                node_x, node_y, text=last_name,
                font=('Arial', 10, 'bold'), fill='#ffffff', tags=node_id
            )

        # Рисуем связи пути
        for i in range(len(people_in_path) - 1):
            person1 = people_in_path[i]
            person2 = people_in_path[i + 1]

            node1 = f"node_{person1.full_name}"
            node2 = f"node_{person2.full_name}"

            x1, y1 = self.node_positions[node1]
            x2, y2 = self.node_positions[node2]

            # Находим тип связи между этими людьми
            rel_type = "связь"
            for rel in person1.relations:
                if isinstance(rel[1], Person) and rel[1].full_name == person2.full_name:
                    rel_type = rel[0]
                    break

            # Рисуем линию связи (толстую красную для выделения)
            graph_canvas.create_line(
                x1, y1, x2, y2,
                arrow=tk.LAST, fill='#ff0000', width=4
            )

            # Подпись связи (посередине линии)
            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2

            graph_canvas.create_text(
                label_x, label_y, text=rel_type,
                font=('Arial', 8, 'bold'), fill=self.graph_settings['text_color']
            )

    def cluster_people(self):
        """Кластеризует людей по группам с помощью ML"""
        if len(self.people) < 2:
            messagebox.showinfo("Информация", "Недостаточно данных для кластеризации")
            return

        # Строим матрицу признаков для кластеризации
        features = []
        people_list = list(self.people.values())

        for person in people_list:
            # Используем количество связей, телефонов, адресов и т.д. как признаки
            feature = [
                len(person.phones),
                len(person.emails),
                len(person.addresses),
                len(person.relations),
                len(person.jobs),
                len(person.social_media),
                len(person.bank_accounts)
            ]
            features.append(feature)

        # Определяем оптимальное количество кластеров (но не более 5)
        n_clusters = min(5, len(people_list))

        # Выполняем кластеризацию
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features)

        # Сохраняем кластеры
        self.clusters = {}
        for i, person in enumerate(people_list):
            self.clusters[person.id] = clusters[i]

        messagebox.showinfo("Успех", f"Люди разделены на {n_clusters} кластера(ов)")

    def apply_filters(self):
        """Применяет фильтры и сортировку к списку людей"""
        sort_by = self.sort_var.get()
        group_by = self.group_var.get()

        people_list = list(self.people.values())

        # Сортировка
        if sort_by == "по имени":
            people_list.sort(key=lambda p: p.full_name)
        elif sort_by == "по дате рождения":
            people_list.sort(key=lambda p: p.birth_date or "9999-99-99")
        elif sort_by == "по количеству связей":
            people_list.sort(key=lambda p: len(p.relations), reverse=True)

        # Группировка
        if group_by == "по кластерам":
            if not self.clusters:
                self.cluster_people()

            # Группируем по кластерам
            clusters = defaultdict(list)
            for person in people_list:
                clusters[self.clusters.get(person.id, -1)].append(person)

            # Обновляем список
            self.people_listbox.delete(0, tk.END)
            for cluster_id in sorted(clusters.keys()):
                self.people_listbox.insert(tk.END, f"=== Кластер {cluster_id + 1} ===")
                for person in clusters[cluster_id]:
                    self.people_listbox.insert(tk.END, str(person))
                self.people_listbox.insert(tk.END, "")

            return
        elif group_by == "по категориям":
            # Группируем по категориям связей
            categories = defaultdict(list)
            for person in people_list:
                category = "Другие"
                for rel in person.relations:
                    if isinstance(rel[1], Person):
                        if 'семь' in rel[0].lower() or 'супруг' in rel[0].lower():
                            category = "Семья"
                            break
                        elif 'работ' in rel[0].lower() or 'коллег' in rel[0].lower():
                            category = "Коллеги"
                            break
                        elif 'друг' in rel[0].lower():
                            category = "Друзья"
                            break
                categories[category].append(person)

            # Обновляем список
            self.people_listbox.delete(0, tk.END)
            for category in sorted(categories.keys()):
                self.people_listbox.insert(tk.END, f"=== {category} ===")
                for person in categories[category]:
                    self.people_listbox.insert(tk.END, str(person))
                self.people_listbox.insert(tk.END, "")

            return

        # Без группировки - просто обновляем список
        self.people_listbox.delete(0, tk.END)
        for person in people_list:
            self.people_listbox.insert(tk.END, str(person))

    def show_statistics(self):
        """Показывает статистику по данным"""
        if not self.people:
            messagebox.showwarning("Предупреждение", "Нет данных для отображения статистики")
            return

        stats_window = tk.Toplevel(self.root)
        stats_window.title("Статистика данных")
        stats_window.geometry("600x500")

        # Основные статистики
        num_people = len(self.people)
        num_phones = sum(len(p.phones) for p in self.people.values())
        avg_phones = num_phones / num_people if num_people > 0 else 0
        num_emails = sum(len(p.emails) for p in self.people.values())
        avg_emails = num_emails / num_people if num_people > 0 else 0
        num_relations = sum(len(p.relations) for p in self.people.values())
        avg_relations = num_relations / num_people if num_people > 0 else 0

        # Центральные фигуры (по количеству связей)
        central_people = sorted(self.people.values(), key=lambda p: len(p.relations), reverse=True)[:5]

        # Мосты между группами (люди с связями в разных кластерах)
        bridges = []
        if self.clusters:
            for person in self.people.values():
                clusters_connected = set()
                for rel in person.relations:
                    if isinstance(rel[1], Person):
                        if self.clusters.get(person.id, -1) != self.clusters.get(rel[1].id, -1):
                            clusters_connected.add(self.clusters.get(rel[1].id, -1))
                if len(clusters_connected) > 1:
                    bridges.append(person)

        # Создаем текст статистики
        stats_text = f"""
        Общая статистика:
        - Всего людей: {num_people}
        - Всего телефонов: {num_phones} (в среднем {avg_phones:.1f} на человека)
        - Всего email: {num_emails} (в среднем {avg_emails:.1f} на человека)
        - Всего связей: {num_relations} (в среднем {avg_relations:.1f} на человека)

        Центральные фигуры (по количеству связей):
        """

        for i, person in enumerate(central_people, 1):
            stats_text += f"\n{i}. {person.full_name} - {len(person.relations)} связей"

        if bridges:
            stats_text += "\n\nМосты между группами (люди, связывающие разные кластеры):"
            for person in bridges[:5]:  # Показываем только топ-5
                stats_text += f"\n- {person.full_name}"

        # Паттерны (люди с одинаковыми телефонами)
        phone_to_people = defaultdict(list)
        for person in self.people.values():
            for phone in person.phones:
                phone_to_people[phone].append(person)

        common_phones = {phone: people for phone, people in phone_to_people.items() if len(people) > 1}
        if common_phones:
            stats_text += "\n\nОбщие телефоны:"
            for phone, people in list(common_phones.items())[:5]:  # Показываем только топ-5
                names = ", ".join(p.full_name.split()[0] for p in people)
                stats_text += f"\n- {phone}: {names}"

        # Отображаем статистику
        text_frame = ttk.Frame(stats_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        text_widget.insert(tk.END, stats_text)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(stats_window, text="Закрыть", command=stats_window.destroy).pack(pady=10)

    def show_on_map_from_list(self):
        """Показывает выбранного человека на карте"""
        selection = self.people_listbox.curselection()
        if not selection:
            return

        selected_person = self.people_listbox.get(selection[0])
        for person in self.people.values():
            if str(person) == selected_person:
                self.show_on_map(person)
                break

    def show_on_map(self, person):
        """Показывает адреса человека на карте"""
        if not person.addresses:
            messagebox.showinfo("Информация", "Нет адресов для отображения")
            return

        map_window = tk.Toplevel(self.root)
        map_window.title(f"Карта для {person.full_name}")
        map_window.geometry("800x600")

        # Создаем фрейм для карты
        map_frame = ttk.Frame(map_window)
        map_frame.pack(fill=tk.BOTH, expand=True)

        # Создаем фигуру matplotlib
        fig, ax = plt.subplots(figsize=(8, 6))
        canvas = FigureCanvasTkAgg(fig, master=map_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Геокодируем адреса
        locations = []
        for address in person.addresses:
            if address in self.geocoded_addresses:
                locations.append(self.geocoded_addresses[address])
            else:
                try:
                    location = self.geolocator.geocode(address)
                    if location:
                        self.geocoded_addresses[address] = (location.latitude, location.longitude)
                        locations.append((location.latitude, location.longitude))
                except GeocoderTimedOut:
                    continue

        if not locations:
            ax.text(0.5, 0.5, "Не удалось геокодировать адреса",
                    ha='center', va='center', fontsize=12)
            canvas.draw()
            return

        # Рисуем точки на карте
        lats = [loc[0] for loc in locations]
        lons = [loc[1] for loc in locations]

        # Вычисляем границы карты
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Добавляем небольшой отступ
        lat_padding = (max_lat - min_lat) * 0.1
        lon_padding = (max_lon - min_lon) * 0.1

        ax.set_xlim(min_lon - lon_padding, max_lon + lon_padding)
        ax.set_ylim(min_lat - lat_padding, max_lat + lat_padding)

        # Рисуем точки
        ax.scatter(lons, lats, c='red', s=100)

        # Подписи точек
        for i, (lat, lon) in enumerate(locations):
            ax.text(lon, lat, f"{i + 1}", ha='center', va='center', color='white')

        # Линии между точками (если их несколько)
        if len(locations) > 1:
            lines = LineCollection([[(lon, lat) for lat, lon in locations]], colors='blue')
            ax.add_collection(lines)

        ax.set_title(f"Адреса {person.full_name}")
        ax.set_xlabel("Долгота")
        ax.set_ylabel("Широта")
        ax.grid(True)

        canvas.draw()

    def create_backup(self):
        """Создает резервную копию данных"""
        if not self.people:
            messagebox.showwarning("Предупреждение", "Нет данных для резервного копирования")
            return

        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_{timestamp}.json")

            data_to_save = {
                'people': [person.to_dict() for person in self.people.values()],
                'timestamp': timestamp,
                'version': '1.0'
            }

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("Успех", f"Резервная копия успешно создана:\n{backup_path}")
            self.log_action("Создание резервной копии", backup_path)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при создании резервной копии:\n{str(e)}")
            self.logger.error(f"Ошибка при создании резервной копии: {str(e)}")

    def restore_from_backup(self):
        """Восстанавливает данные из резервной копии"""
        backup_path = filedialog.askopenfilename(
            title="Выберите файл резервной копии",
            filetypes=(("JSON файлы", "*.json"), ("Все файлы", "*.*"))
        )

        if not backup_path:
            return

        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Очищаем текущие данные
            self.people = {}
            self.current_person = None
            self.graph_objects = []
            self.search_results = []
            self.file_path = None
            self.selected_node = None
            self.node_positions = {}
            self.people_to_merge = set()
            self.people_to_analyze = set()
            self.current_file_people = set()
            self.graph = nx.Graph()
            self.clusters = {}

            # Восстанавливаем людей
            for person_data in backup_data.get('people', []):
                person = Person(person_data['full_name'], person_data.get('birth_date'))
                person.id = person_data.get('id', str(uuid.uuid4()))
                person.phones = set(person_data.get('phones', []))
                person.emails = set(person_data.get('emails', []))
                person.addresses = set(person_data.get('addresses', []))
                person.passports = set(person_data.get('passports', []))
                person.cars = set(person_data.get('cars', []))
                person.jobs = set(person_data.get('jobs', []))
                person.social_media = defaultdict(set,
                                                  {k: set(v) for k, v in person_data.get('social_media', {}).items()})
                person.bank_accounts = set(person_data.get('bank_accounts', []))
                person.aliases = set(person_data.get('aliases', []))
                person.source_files = set(person_data.get('source_files', []))
                person.driver_license = person_data.get('driver_license')
                person.snils = person_data.get('snils')
                person.inn = person_data.get('inn')
                person.created_at = person_data.get('created_at', datetime.now().isoformat())
                person.updated_at = person_data.get('updated_at', datetime.now().isoformat())
                person.created_by = person_data.get('created_by', 'system')
                person.updated_by = person_data.get('updated_by', 'system')

                # Восстанавливаем связи (пока только имена)
                for rel_data in person_data.get('relations', []):
                    related_person_name = rel_data['related_person']
                    rel_type = rel_data['type']
                    details = rel_data.get('details', {})
                    person.relations.add((rel_type, related_person_name, tuple(sorted(details.items()))))

                # Сохраняем человека
                key = (person.full_name.lower(), person.birth_date)
                self.people[key] = person

            # Восстанавливаем реальные связи между объектами Person
            for person in self.people.values():
                new_relations = set()
                for rel_type, related_person, frozen_details in person.relations:
                    if not isinstance(related_person, Person):
                        # Ищем человека по имени
                        found = None
                        for p in self.people.values():
                            if p.full_name == related_person:
                                found = p
                                break
                        if found:
                            new_relations.add((rel_type, found, frozen_details))
                        else:
                            new_relations.add((rel_type, related_person, frozen_details))
                    else:
                        new_relations.add((rel_type, related_person, frozen_details))

                person.relations = new_relations

            self.update_people_list()
            messagebox.showinfo("Успех", f"Данные успешно восстановлены из:\n{backup_path}")
            self.log_action("Восстановление из резервной копии", backup_path)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при восстановлении из резервной копии:\n{str(e)}")
            self.logger.error(f"Ошибка при восстановлении из резервной копии: {str(e)}")

    def auto_detect_relations(self):
        """Автоматически определяет типы связей на основе общих данных"""
        if not self.people:
            return

        self.status_bar.config(text="Автоматическое определение связей...")
        self.log_action("Автоматическое определение связей", "начато")

        detected = 0

        # Проходим по всем парам людей
        people_list = list(self.people.values())
        for i in range(len(people_list)):
            for j in range(i + 1, len(people_list)):
                person1 = people_list[i]
                person2 = people_list[j]

                # Проверяем, есть ли уже связь между этими людьми
                has_relation = any(
                    isinstance(rel[1], Person) and rel[1].full_name == person2.full_name
                    for rel in person1.relations
                )
                if has_relation:
                    continue

                # Проверяем общие данные
                common_addresses = person1.addresses & person2.addresses
                common_phones = person1.phones & person2.phones
                common_jobs = person1.jobs & person2.jobs

                # Определяем тип связи
                relation_type = None
                if common_addresses and not common_jobs:
                    relation_type = "семейная связь"
                elif common_jobs and not common_addresses:
                    relation_type = "коллега"
                elif common_addresses and common_jobs:
                    relation_type = "возможная связь"
                elif common_phones:
                    relation_type = "знакомый"

                if relation_type:
                    details = {
                        'reason': 'автоматически определенная связь',
                        'source_files': list(person1.source_files | person2.source_files)
                    }
                    if common_addresses:
                        details['common_addresses'] = list(common_addresses)
                    if common_phones:
                        details['common_phones'] = list(common_phones)
                    if common_jobs:
                        details['common_jobs'] = list(common_jobs)

                    person1.add_relation(relation_type, person2, details)
                    detected += 1

        self.status_bar.config(text=f"Определено {detected} новых связей")
        self.log_action("Автоматическое определение связей", f"определено {detected} связей")
        messagebox.showinfo("Успех", f"Автоматически определено {detected} новых связей")

    # Остальные методы класса остаются без изменений (add_relation_dialog, set_api_key, analyze_with_chatgpt и т.д.)
    # ...

        # Находим выбранного человека
        related_person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                related_person = p
                break

        if not related_person or related_person == self.current_person:
            return

        # Диалог для ввода типа связи
        relation_type = simpledialog.askstring(
            "Добавить связь",
            f"Введите тип связи между {self.current_person.full_name} и {related_person.full_name}:",
            parent=self.root
        )

        if relation_type:
            # Добавляем информацию о файлах-источниках
            details = {}
            if self.current_person.source_files:
                details['source_files'] = list(self.current_person.source_files)
            if related_person.source_files:
                if 'source_files' in details:
                    details['source_files'].extend(list(related_person.source_files))
                else:
                    details['source_files'] = list(related_person.source_files)

            # Убираем дубликаты
            if 'source_files' in details:
                details['source_files'] = list(set(details['source_files']))

            # Добавляем причину связи
            if self.current_person.source_files & related_person.source_files:
                details['reason'] = 'из одного файла'
            else:
                details['reason'] = 'вручную добавленная связь'

            self.current_person.add_relation(relation_type, related_person, details)
            self.show_relations()
            messagebox.showinfo("Успех", "Связь успешно добавлена")
    def set_api_key(self):
        """Устанавливает API ключ для OpenAI"""
        self.openai_api_key = self.api_key_entry.get()
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            messagebox.showinfo("Успех", "API ключ установлен")
        else:
            messagebox.showwarning("Предупреждение", "Введите API ключ")

    def analyze_with_chatgpt(self):
        """Анализирует данные с помощью ChatGPT"""
        if not self.openai_api_key:
            messagebox.showwarning("Предупреждение", "Сначала установите API ключ OpenAI")
            return

        if not self.current_person and not self.people_to_analyze:
            messagebox.showwarning("Предупреждение", "Сначала выберите человека или группу людей для анализа")
            return

        # Определяем, анализируем одного человека или группу
        if self.people_to_analyze:
            people_to_analyze = list(self.people_to_analyze)
            self.people_to_analyze.clear()  # Очищаем список после использования
        else:
            people_to_analyze = [self.current_person]

        # Формируем промпт для анализа
        if len(people_to_analyze) == 1:
            prompt = self._create_single_person_prompt(people_to_analyze[0])
        else:
            prompt = self._create_group_prompt(people_to_analyze)

        # Запускаем анализ в отдельном потоке
        def run_analysis():
            try:
                self.status_bar.config(text="Анализ с ChatGPT...")

                response = openai.ChatCompletion.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system",
                         "content": "Ты аналитик данных, который помогает анализировать информацию о людях и их связях. Особое внимание уделяй источникам информации и причинам связей между людьми."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )

                analysis_result = response.choices[0].message.content

                # Показываем результат в новом окне
                self.show_analysis_result(analysis_result)
                self.status_bar.config(text="Анализ завершен")

            except Exception as e:
                self.status_bar.config(text="Ошибка анализа")
                messagebox.showerror("Ошибка", f"Ошибка при анализе с ChatGPT:\n{str(e)}")

        threading.Thread(target=run_analysis).start()

    def _create_single_person_prompt(self, person):
        """Создает промпт для анализа одного человека"""
        prompt = (
            f"Проанализируй данные о человеке и его связях:\n\n"
            f"Имя: {person.full_name}\n"
            f"Дата рождения: {person.birth_date or 'неизвестна'}\n"
            f"Телефоны: {', '.join(person.phones) if person.phones else 'нет данных'}\n"
            f"Email: {', '.join(person.emails) if person.emails else 'нет данных'}\n"
            f"Адреса: {', '.join(person.addresses) if person.addresses else 'нет данных'}\n"
            f"Связи:\n"
        )

        for rel_type, related_person, frozen_details in person.relations:
            details = dict(frozen_details)  # Преобразуем обратно в словарь
            if isinstance(related_person, Person):
                rel_text = f"- {rel_type}: {related_person.full_name}"
            else:
                rel_text = f"- {rel_type}: {related_person}"

            # Добавляем информацию об источниках и причинах
            if details:
                details_text = []
                if 'source_files' in details:
                    details_text.append(f"источники: {', '.join(details['source_files'])}")
                if 'reason' in details:
                    details_text.append(f"причина: {details['reason']}")
                if details_text:
                    rel_text += f" ({'; '.join(details_text)})"

            prompt += rel_text + "\n"

        prompt += (
            "\nПроанализируй эту информацию и ответь на следующие вопросы:\n"
            "1. Какие основные характеристики этого человека можно выделить?\n"
            "2. Какие интересные закономерности или связи можно отметить? Обрати особое внимание на источники и причины связей.\n"
            "3. Какие потенциальные риски или необычные аспекты можно выделить?\n"
            "4. Какие дополнительные данные было бы полезно собрать?\n"
            "5. Расширенная информация о связях (источники, причины, возможные скрытые взаимосвязи).\n"
            "\nОтветь на русском языке, в формате маркированного списка."
        )
        return prompt

    def _create_group_prompt(self, people):
        """Создает промпт для анализа группы людей"""
        prompt = (
            "Проанализируй данные о группе людей и их взаимосвязях:\n\n"
            "Список людей и их основные данные:\n"
        )

        # Добавляем информацию о каждом человеке
        for person in people:
            prompt += (
                f"\nИмя: {person.full_name}\n"
                f"Дата рождения: {person.birth_date or 'неизвестна'}\n"
                f"Телефоны: {', '.join(person.phones) if person.phones else 'нет данных'}\n"
                f"Email: {', '.join(person.emails) if person.emails else 'нет данных'}\n"
                f"Адреса: {', '.join(person.addresses) if person.addresses else 'нет данных'}\n"
            )

            # Добавляем уникальные связи между людьми в группе
            group_relations = []
            for rel_type, related_person, frozen_details in person.relations:
                if isinstance(related_person, Person) and related_person in people:
                    details = dict(frozen_details)
                    rel_text = f"- {rel_type}: {related_person.full_name}"

                    if details:
                        details_text = []
                        if 'source_files' in details:
                            details_text.append(f"источники: {', '.join(details['source_files'])}")
                        if 'reason' in details:
                            details_text.append(f"причина: {details['reason']}")
                        if details_text:
                            rel_text += f" ({'; '.join(details_text)})"

                    group_relations.append(rel_text)

            if group_relations:
                prompt += "Связи с другими людьми в группе:\n" + "\n".join(group_relations) + "\n"

        prompt += (
            "\nПроанализируй эту информацию и ответь на следующие вопросы:\n"
            "1. Какие общие характеристики можно выделить у этой группы людей?\n"
            "2. Какие интересные закономерности или связи можно отметить между ними? Обрати особое внимание на источники и причины связей.\n"
            "3. Какие потенциальные риски или необычные аспекты можно выделить в этой группе?\n"
            "4. Как эти люди могут быть связаны между собой, помимо явных связей?\n"
            "5. Какие дополнительные данные было бы полезно собрать для лучшего понимания их отношений?\n"
            "6. Какие выводы можно сделать об их возможных общих интересах или деятельности?\n"
            "\nОтветь на русском языке, в формате маркированного списка."
        )
        return prompt

    def show_analysis_result(self, result):
        """Показывает результат анализа ChatGPT"""
        result_window = tk.Toplevel(self.root)
        result_window.title("Результат анализа ChatGPT")
        result_window.geometry("800x600")

        text_frame = ttk.Frame(result_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        text_widget.insert(tk.END, result)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(result_window, text="Закрыть", command=result_window.destroy).pack(pady=10)

    def show_people_list_menu(self, event):
        """Показывает контекстное меню для списка людей"""
        self.people_list_menu.post(event.x_root, event.y_root)

    def show_selected_list_person_info(self):
        """Показывает информацию о выбранном в списке человеке"""
        selection = self.people_listbox.curselection()
        if not selection:
            return

        selected_person = self.people_listbox.get(selection[0])
        for person in self.people.values():
            if str(person) == selected_person:
                self.current_person = person
                self.show_person_info()
                break

    def add_relation_from_list(self):
        """Добавляет связь между выбранными в списке людьми"""
        selections = self.people_listbox.curselection()
        if len(selections) != 2:
            messagebox.showwarning("Предупреждение", "Выберите ровно двух человек для создания связи")
            return

        person1_str = self.people_listbox.get(selections[0])
        person2_str = self.people_listbox.get(selections[1])

        person1 = None
        person2 = None

        # Находим объекты выбранных людей
        for person in self.people.values():
            if str(person) == person1_str:
                person1 = person
            if str(person) == person2_str:
                person2 = person
            if person1 and person2:
                break

        if not person1 or not person2:
            messagebox.showerror("Ошибка", "Не удалось найти выбранных людей")
            return

        # Диалог для ввода типа связи
        relation_type = simpledialog.askstring(
            "Добавить связь",
            f"Введите тип связи между {person1.full_name} и {person2.full_name}:",
            parent=self.root
        )

        if relation_type:
            # Добавляем информацию о файлах-источниках
            details = {}
            if person1.source_files:
                details['source_files'] = list(person1.source_files)
            if person2.source_files:
                if 'source_files' in details:
                    details['source_files'].extend(list(person2.source_files))
                else:
                    details['source_files'] = list(person2.source_files)

            # Убираем дубликаты
            if 'source_files' in details:
                details['source_files'] = list(set(details['source_files']))

            # Добавляем причину связи
            if person1.source_files & person2.source_files:
                details['reason'] = 'из одного файла'
            else:
                details['reason'] = 'вручную добавленная связь'

            person1.add_relation(relation_type, person2, details)
            self.show_relations()
            messagebox.showinfo("Успех", "Связь успешно добавлена")

    def remove_relation_from_list(self):
        """Удаляет связь между выбранными в списке людьми"""
        selections = self.people_listbox.curselection()
        if len(selections) != 2:
            messagebox.showwarning("Предупреждение", "Выберите ровно двух человек для удаления связи")
            return

        person1_str = self.people_listbox.get(selections[0])
        person2_str = self.people_listbox.get(selections[1])

        person1 = None
        person2 = None

        # Находим объекты выбранных людей
        for person in self.people.values():
            if str(person) == person1_str:
                person1 = person
            if str(person) == person2_str:
                person2 = person
            if person1 and person2:
                break

        if not person1 or not person2:
            messagebox.showerror("Ошибка", "Не удалось найти выбранных людей")
            return

        # Получаем список связей между этими людьми
        relations = []
        for rel in person1.relations:
            if isinstance(rel[1], Person) and rel[1].full_name == person2.full_name:
                relations.append(rel[0])

        if not relations:
            messagebox.showinfo("Информация", "Нет связей для удаления")
            return

        # Диалог выбора связи для удаления
        relation_type = simpledialog.askstring(
            "Удалить связь",
            f"Введите тип связи между {person1.full_name} и {person2.full_name} для удаления:\n"
            f"Доступные связи: {', '.join(relations)}",
            parent=self.root
        )

        if relation_type and relation_type in relations:
            if person1.remove_relation(relation_type, person2):
                messagebox.showinfo("Успех", "Связь успешно удалена")
                self.show_relations()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить связь")

    def add_to_merge_list_from_list(self):
        """Добавляет выбранных в списке людей в список для объединения"""
        selections = self.people_listbox.curselection()
        if not selections:
            messagebox.showwarning("Предупреждение", "Выберите людей для объединения")
            return

        for index in selections:
            person_str = self.people_listbox.get(index)
            for person in self.people.values():
                if str(person) == person_str:
                    self.people_to_merge.add(person)
                    break

        messagebox.showinfo("Информация",
                            f"Добавлено {len(selections)} человек в список для объединения. Всего: {len(self.people_to_merge)}")

    def add_to_analysis_list_from_list(self):
        """Добавляет выбранных в списке людей в список для анализа"""
        selections = self.people_listbox.curselection()
        if not selections:
            messagebox.showwarning("Предупреждение", "Выберите людей для анализа")
            return

        for index in selections:
            person_str = self.people_listbox.get(index)
            for person in self.people.values():
                if str(person) == person_str:
                    self.people_to_analyze.add(person)
                    break

        messagebox.showinfo("Информация",
                            f"Добавлено {len(selections)} человек в список для анализа. Всего: {len(self.people_to_analyze)}")

    def delete_selected_person_from_list(self):
        """Удаляет выбранного в списке человека"""
        selections = self.people_listbox.curselection()
        if not selections:
            messagebox.showwarning("Предупреждение", "Выберите человека для удаления")
            return

        # Подтверждение удаления
        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить выбранного человека?"):
            return

        # Получаем список выбранных людей
        people_to_delete = []
        for index in selections:
            person_str = self.people_listbox.get(index)
            for key, person in list(self.people.items()):
                if str(person) == person_str:
                    people_to_delete.append((key, person))
                    break

        # Удаляем людей и все связанные с ними связи
        deleted_count = 0
        for key, person in people_to_delete:
            # Удаляем все связи с этим человеком
            for other_person in self.people.values():
                to_remove = []
                for rel in other_person.relations:
                    if isinstance(rel[1], Person) and rel[1].full_name == person.full_name:
                        to_remove.append(rel)

                for rel in to_remove:
                    other_person.relations.remove(rel)

            # Удаляем самого человека
            if key in self.people:
                del self.people[key]
                deleted_count += 1

        self.update_people_list()
        messagebox.showinfo("Успех", f"Удалено {deleted_count} человек")

    def merge_selected_people(self):
        """Объединяет выбранных людей"""
        if len(self.people_to_merge) < 2:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы двух человек для объединения")
            return

        # Выбираем основного человека (с наибольшим количеством данных)
        main_person = max(self.people_to_merge, key=lambda p: len(p.phones) + len(p.emails) + len(p.addresses))
        self.people_to_merge.remove(main_person)

        # Объединяем остальных с основным
        merged_count = 0
        for person in list(self.people_to_merge):
            if main_person.merge(person):
                # Удаляем объединенного человека
                key = (person.full_name.lower(), person.birth_date)
                if key in self.people:
                    del self.people[key]
                merged_count += 1

        self.people_to_merge.clear()
        self.update_people_list()

        if merged_count > 0:
            messagebox.showinfo("Успех", f"Объединено {merged_count} человек с {main_person.full_name}")
            self.current_person = main_person
            self.show_person_info()
        else:
            messagebox.showinfo("Информация", "Не удалось объединить выбранных людей")

    def show_graph_menu(self, event):
        """Показывает контекстное меню для графа"""
        # Определяем, был ли клик по узлу
        self.selected_node = None
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        for node_id, (node_x, node_y) in self.node_positions.items():
            if (node_x - 60 <= x <= node_x + 60 and
                    node_y - 40 <= y <= node_y + 40):
                self.selected_node = node_id
                break

        if self.selected_node:
            self.graph_menu.post(event.x_root, event.y_root)

    def show_selected_node_info(self):
        """Показывает информацию о выбранном узле в графе"""
        if not self.selected_node:
            return

        # Находим человека по ID узла
        person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                person = p
                break

        if person:
            self.current_person = person
            self.show_person_info()

    def add_to_merge_list(self):
        """Добавляет выбранного в графе человека в список для объединения"""
        if not self.selected_node:
            return

        # Находим человека по ID узла
        person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                person = p
                break

        if person:
            self.people_to_merge.add(person)
            messagebox.showinfo("Информация",
                                f"{person.full_name} добавлен в список для объединения. Всего: {len(self.people_to_merge)}")

    def add_to_analysis_list(self):
        """Добавляет выбранного в графе человека в список для анализа"""
        if not self.selected_node:
            return

        # Находим человека по ID узла
        person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                person = p
                break

        if person:
            self.people_to_analyze.add(person)
            messagebox.showinfo("Информация",
                                f"{person.full_name} добавлен в список для анализа. Всего: {len(self.people_to_analyze)}")

    def delete_selected_person(self):
        """Удаляет выбранного в графе человека"""
        if not self.selected_node:
            return

        # Находим человека по ID узла
        person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                person = p
                break

        if not person:
            return

        # Подтверждение удаления
        if not messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить {person.full_name}?"):
            return

        # Удаляем все связи с этим человеком
        for other_person in self.people.values():
            to_remove = []
            for rel in other_person.relations:
                if isinstance(rel[1], Person) and rel[1].full_name == person.full_name:
                    to_remove.append(rel)

            for rel in to_remove:
                other_person.relations.remove(rel)

        # Удаляем самого человека
        key = (person.full_name.lower(), person.birth_date)
        if key in self.people:
            del self.people[key]
            self.update_people_list()
            self.clear_canvas()
            messagebox.showinfo("Успех", f"{person.full_name} успешно удален")

    def remove_relation_dialog(self):
        """Диалог удаления связи"""
        if not self.selected_node or not self.current_person:
            return

        # Находим выбранного человека
        related_person = None
        for p in self.people.values():
            if f"node_{p.full_name}" == self.selected_node:
                related_person = p
                break

        if not related_person or related_person == self.current_person:
            return

        # Получаем список связей между этими людьми
        relations = []
        for rel in self.current_person.relations:
            if isinstance(rel[1], Person) and rel[1].full_name == related_person.full_name:
                relations.append(rel[0])

        if not relations:
            messagebox.showinfo("Информация", "Нет связей для удаления")
            return

        # Диалог выбора связи для удаления
        relation_type = simpledialog.askstring(
            "Удалить связь",
            f"Введите тип связи между {self.current_person.full_name} и {related_person.full_name} для удаления:\n"
            f"Доступные связи: {', '.join(relations)}",
            parent=self.root
        )

        if relation_type and relation_type in relations:
            if self.current_person.remove_relation(relation_type, related_person):
                messagebox.showinfo("Успех", "Связь успешно удалена")
                self.show_relations()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить связь")

    def open_folder(self):
        """Открывает папку с файлами данных"""
        folder_path = filedialog.askdirectory(title="Выберите папку с файлами данных")
        if folder_path:
            self.process_folder(folder_path)

    def process_folder(self, folder_path):
        """Обрабатывает все txt файлы в папке"""
        txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        if not txt_files:
            messagebox.showwarning("Предупреждение", "В папке нет txt файлов")
            return

        self.status_bar.config(text=f"Обработка {len(txt_files)} файлов...")

        # Обрабатываем каждый файл
        for filename in txt_files:
            self.current_file_people = set()  # Сбрасываем список людей для текущего файла
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            self.parse_data(content, source_file=filename)

            # Создаем связи между всеми людьми из одного файла
            self.create_relations_within_file()

        # После загрузки всех файлов устанавливаем связи между людьми из разных файлов
        self.create_cross_file_relations()

        self.update_people_list()
        self.status_bar.config(text=f"Загружено {len(txt_files)} файлов | Людей: {len(self.people)}")
        messagebox.showinfo("Успех", f"Обработано {len(txt_files)} файлов, найдено {len(self.people)} человек")

    def create_relations_within_file(self):
        """Создает связи между всеми людьми из одного файла"""
        if len(self.current_file_people) < 2:
            return

        people_list = list(self.current_file_people)
        for i in range(len(people_list)):
            for j in range(i + 1, len(people_list)):
                person1 = people_list[i]
                person2 = people_list[j]

                # Добавляем связь с указанием источника и причины
                details = {
                    'source_files': list(person1.source_files),
                    'reason': 'из одного файла'
                }
                person1.add_relation("связь", person2, details)

    def create_cross_file_relations(self):
        """Создает связи между людьми из разных файлов с одинаковыми именами"""
        people_by_name = defaultdict(list)
        for person in self.people.values():
            name_key = (person.full_name.split()[0], person.full_name.split()[1])  # Фамилия и имя
            people_by_name[name_key].append(person)

        # Для каждой группы людей с одинаковыми фамилией и именем
        for name_key, people_group in people_by_name.items():
            if len(people_group) > 1:
                # Сортируем по количеству файлов-источников
                people_group.sort(key=lambda p: len(p.source_files), reverse=True)
                main_person = people_group[0]

                # Добавляем связи с остальными
                for person in people_group[1:]:
                    # Проверяем, что люди из разных файлов
                    if not main_person.source_files.intersection(person.source_files):
                        details = {
                            'source_files': list(main_person.source_files) + list(person.source_files),
                            'reason': 'одинаковые фамилия и имя в разных файлах'
                        }
                        main_person.add_relation("возможная связь", person, details)

    def parse_data(self, content, source_file=None):
        """Парсит данные из текста файла"""
        sections = re.split(r'=== (.*?) ===', content)[1:]

        for i in range(0, len(sections), 2):
            section_name = sections[i].strip()
            section_content = sections[i + 1].strip()

            if not section_name or not section_content:
                continue

            self.parse_section(section_name, section_content, source_file)

    def parse_section(self, section_name, section_content, source_file=None):
        lines = [line.strip() for line in section_content.split('\n') if line.strip()]

        # Общая сводка
        if section_name.lower().startswith('общая сводка'):
            self.parse_general_summary(lines, source_file)

        # Все остальные разделы
        else:
            person_data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    person_data[key.strip().lower()] = value.strip()

            self.process_person_data(person_data, section_name, source_file)

    def parse_general_summary(self, lines, source_file=None):
        current_person = None
        data = {}

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                data[key] = value
            elif line.startswith('---'):
                if data:
                    self.process_person_data(data, "Общая сводка", source_file)
                    data = {}

        if data:
            self.process_person_data(data, "Общая сводка", source_file)

    def process_person_data(self, data, source, source_file=None):
        # Извлекаем основные данные о человеке
        full_name = None
        birth_date = None

        # Пытаемся найти имя в разных полях
        for field in ['фио', 'имя клиента', 'наименование клиента', 'фам', 'ф.и.о.', 'личности']:
            if field in data:
                name_data = data[field]
                # Извлекаем все возможные имена из строки
                names = re.findall(r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?', name_data)
                if names:
                    full_name = names[0]
                    break

                # Пробуем извлечь имя из строк типа "Коваль Павел Павлович 05.08.1990"
                name_parts = re.split(r'\s+', name_data)
                if len(name_parts) >= 3 and re.match(r'\d{2}\.\d{2}\.\d{4}', name_parts[-1]):
                    full_name = ' '.join(name_parts[:3])
                    birth_date = name_parts[-1]
                    break

        # Если имя не найдено, пропускаем запись
        if not full_name:
            return

        # Пытаемся найти дату рождения
        if not birth_date:
            for field in ['день рождения', 'дата рождения', 'birth_date', 'дата']:
                if field in data:
                    date_str = data[field]
                    if re.match(r'\d{2}\.\d{2}\.\d{4}', date_str):
                        birth_date = date_str
                        break
                    elif re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                        birth_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
                        break

        # Создаем или получаем объект человека
        person = self._get_or_create_person(full_name, birth_date)
        if source_file:
            person.source_files.add(source_file)
            self.current_file_people.add(person)  # Добавляем человека в список текущего файла

        # Добавляем телефоны
        if 'телефон' in data:
            phones = re.findall(r'[\d\(\)\+\- ]{7,}', data['телефон'])
            for phone in phones:
                clean_phone = re.sub(r'[^\d]', '', phone)
                if len(clean_phone) >= 10:
                    person.phones.add(clean_phone)

        # Добавляем email
        if 'email' in data:
            emails = re.findall(r'[\w\.-]+@[\w\.-]+', data['email'])
            person.emails.update(emails)

        # Добавляем адреса
        if 'адрес' in data:
            address = data['адрес']
            if address and len(address) > 5:  # Минимальная длина для адреса
                person.addresses.add(address)

        # Добавляем паспортные данные
        if 'паспорт' in data:
            passport = data['паспорт']
            if passport and len(passport) >= 6:  # Минимальная длина для паспорта
                person.passports.add(passport)

        # Добавляем автомобили
        if 'автомобили' in data:
            cars = re.findall(r'[А-ЯЁа-яё]\d{3}[А-ЯЁа-яё]{2}\d{2,3}', data['автомобили'])
            person.cars.update(cars)

        # Добавляем СНИЛС
        if 'снилс' in data:
            snils = data['снилс']
            if len(snils) >= 11:
                person.snils = snils

        # Добавляем ИНН
        if 'инн' in data:
            inn = data['инн']
            if len(inn) >= 10:
                person.inn = inn

        # Добавляем водительские права
        if 'водительское удостоверение' in data:
            license_num = data['водительское удостоверение']
            if len(license_num) >= 6:
                person.driver_license = license_num

        # Добавляем информацию о работе
        if 'место работы' in data:
            person.jobs.add(data['место работы'])

        # Добавляем социальные сети
        if 'ссылка' in data and ('vk.com' in data['ссылка'] or 'ok.ru' in data['ссылка']):
            person.social_media['vk' if 'vk.com' in data['ссылка'] else 'ok'].add(data['ссылка'])

        # Добавляем банковские счета
        if 'банк' in data or 'счет' in data:
            bank_info = data.get('банк', '') + ' ' + data.get('счет', '')
            if bank_info.strip():
                person.bank_accounts.add(bank_info.strip())

    def _get_or_create_person(self, full_name, birth_date=None):
        normalized_name = Person.normalize_name(full_name)
        key = (normalized_name.lower(), birth_date)

        if key not in self.people:
            self.people[key] = Person(normalized_name, birth_date)

        return self.people[key]

    def update_people_list(self):
        self.people_listbox.delete(0, tk.END)
        for person in sorted(self.people.values(), key=lambda p: p.full_name):
            self.people_listbox.insert(tk.END, str(person))

    def reset_search(self):
        """Сбрасывает результаты поиска и показывает всех людей"""
        self.search_entry.delete(0, tk.END)
        self.search_results = []
        self.update_people_list()
        self.status_bar.config(text="Поиск сброшен")

    def on_person_select(self, event):
        selection = self.people_listbox.curselection()
        if selection:
            selected_person = self.people_listbox.get(selection[0])

            # Находим выбранного человека
            for person in self.people.values():
                if str(person) == selected_person:
                    self.current_person = person
                    self.show_person_info()
                    break

    def show_person_info(self):
        self.clear_canvas()

        if not self.current_person:
            return

        # Создаем Notebook для вкладок
        notebook = ttk.Notebook(self.inner_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка "Основная информация"
        main_info_frame = ttk.Frame(notebook)
        notebook.add(main_info_frame, text="Основная информация")

        # Основная информация
        main_info = [
            f"ФИО: {self.current_person.full_name}",
            f"Дата рождения: {self.current_person.birth_date or 'неизвестна'}"
        ]

        if self.current_person.snils:
            main_info.append(f"СНИЛС: {self.current_person.snils}")
        if self.current_person.inn:
            main_info.append(f"ИНН: {self.current_person.inn}")
        if self.current_person.driver_license:
            main_info.append(f"Водительское удостоверение: {self.current_person.driver_license}")

        if self.current_person.aliases:
            main_info.append(f"\nДругие варианты имени: {', '.join(self.current_person.aliases)}")

        if self.current_person.source_files:
            main_info.append(f"\nИсточники данных: {', '.join(self.current_person.source_files)}")

        main_label = ttk.Label(main_info_frame, text="\n".join(main_info),
                               font=('Arial', 12, 'bold'), justify=tk.LEFT)
        main_label.pack(anchor=tk.W, padx=10, pady=10)

        # Вкладка "Контактные данные"
        contact_frame = ttk.Frame(notebook)
        notebook.add(contact_frame, text="Контактные данные")

        # Телефоны
        if self.current_person.phones:
            phones_frame = ttk.LabelFrame(contact_frame, text="Телефоны", padding=10)
            phones_frame.pack(fill=tk.X, padx=5, pady=5)

            for phone in self.current_person.phones:
                phone_frame = ttk.Frame(phones_frame)
                phone_frame.pack(fill=tk.X, pady=2)
                ttk.Label(phone_frame, text=phone).pack(side=tk.LEFT)
                ttk.Button(phone_frame, text="📞", command=lambda p=phone: self.copy_to_clipboard(p),
                           width=3).pack(side=tk.RIGHT)

        # Email
        if self.current_person.emails:
            email_frame = ttk.LabelFrame(contact_frame, text="Email", padding=10)
            email_frame.pack(fill=tk.X, padx=5, pady=5)

            for email in self.current_person.emails:
                email_frame_inner = ttk.Frame(email_frame)
                email_frame_inner.pack(fill=tk.X, pady=2)
                ttk.Label(email_frame_inner, text=email).pack(side=tk.LEFT)
                ttk.Button(email_frame_inner, text="📧", command=lambda e=email: self.copy_to_clipboard(e),
                           width=3).pack(side=tk.RIGHT)

        # Адреса
        if self.current_person.addresses:
            address_frame = ttk.LabelFrame(contact_frame, text="Адреса", padding=10)
            address_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            for address in self.current_person.addresses:
                ttk.Label(address_frame, text=address, wraplength=600).pack(anchor=tk.W)

        # Вкладка "Документы"
        docs_frame = ttk.Frame(notebook)
        notebook.add(docs_frame, text="Документы")

        # Паспорта
        if self.current_person.passports:
            passport_frame = ttk.LabelFrame(docs_frame, text="Паспорта", padding=10)
            passport_frame.pack(fill=tk.X, padx=5, pady=5)

            for passport in self.current_person.passports:
                ttk.Label(passport_frame, text=passport).pack(anchor=tk.W)

        # Водительские права
        if self.current_person.driver_license:
            license_frame = ttk.LabelFrame(docs_frame, text="Водительские права", padding=10)
            license_frame.pack(fill=tk.X, padx=5, pady=5)

            ttk.Label(license_frame, text=self.current_person.driver_license).pack(anchor=tk.W)

        # Вкладка "Транспорт и собственность"
        property_frame = ttk.Frame(notebook)
        notebook.add(property_frame, text="Транспорт и собственность")

        # Автомобили
        if self.current_person.cars:
            cars_frame = ttk.LabelFrame(property_frame, text="Автомобили", padding=10)
            cars_frame.pack(fill=tk.X, padx=5, pady=5)

            for car in self.current_person.cars:
                ttk.Label(cars_frame, text=car).pack(anchor=tk.W)

        # Вкладка "Финансы"
        finance_frame = ttk.Frame(notebook)
        notebook.add(finance_frame, text="Финансы")

        # Банковские счета
        if self.current_person.bank_accounts:
            bank_frame = ttk.LabelFrame(finance_frame, text="Банковские счета", padding=10)
            bank_frame.pack(fill=tk.X, padx=5, pady=5)

            for account in self.current_person.bank_accounts:
                ttk.Label(bank_frame, text=account).pack(anchor=tk.W)

        # Вкладка "Социальные сети"
        social_frame = ttk.Frame(notebook)
        notebook.add(social_frame, text="Социальные сети")

        # Соцсети
        for platform, accounts in self.current_person.social_media.items():
            if accounts:
                platform_frame = ttk.LabelFrame(social_frame, text=platform.upper(), padding=10)
                platform_frame.pack(fill=tk.X, padx=5, pady=5)

                for account in accounts:
                    account_frame = ttk.Frame(platform_frame)
                    account_frame.pack(fill=tk.X, pady=2)
                    ttk.Label(account_frame, text=account).pack(side=tk.LEFT)
                    ttk.Button(account_frame, text="🌐", command=lambda url=account: webbrowser.open(url),
                               width=3).pack(side=tk.RIGHT)

        # Вкладка "Работа и связи"
        work_frame = ttk.Frame(notebook)
        notebook.add(work_frame, text="Работа и связи")

        # Места работы
        if self.current_person.jobs:
            jobs_frame = ttk.LabelFrame(work_frame, text="Места работы", padding=10)
            jobs_frame.pack(fill=tk.X, padx=5, pady=5)

            for job in self.current_person.jobs:
                ttk.Label(jobs_frame, text=job).pack(anchor=tk.W)

            # Связи
        if self.current_person.relations:
            relations_frame = ttk.LabelFrame(work_frame, text="Связи", padding=10)
            relations_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            for rel_type, related_person, frozen_details in self.current_person.relations:
                details = dict(frozen_details)  # Преобразуем обратно в словарь
                if isinstance(related_person, Person):
                    rel_text = f"{rel_type}: {related_person.full_name}"
                else:
                    rel_text = f"{rel_type}: {related_person}"

                if details:
                    details_text = []
                    if 'source_files' in details:
                        details_text.append(f"источники: {', '.join(details['source_files'])}")
                    if 'reason' in details:
                        details_text.append(f"причина: {details['reason']}")
                    if details_text:
                        rel_text += f" ({'; '.join(details_text)})"

                ttk.Label(relations_frame, text=rel_text, wraplength=600).pack(anchor=tk.W)

    def show_relations(self):
        if not self.current_person:
            messagebox.showwarning("Предупреждение", "Сначала выберите человека из списка")
            return

        self.clear_canvas()
        self.node_positions = {}

        # Создаем холст для графа
        graph_canvas = tk.Canvas(self.inner_frame, width=1000, height=700, bg='white')
        graph_canvas.grid(row=0, column=0, sticky="nsew")
        self.graph_objects.append(graph_canvas)

        # Центральный узел - текущий человек
        center_x, center_y = 500, 350
        node_id = f"node_{self.current_person.full_name}"
        self.node_positions[node_id] = (center_x, center_y)

        graph_canvas.create_oval(center_x - 60, center_y - 40, center_x + 60, center_y + 40,
                                 fill='#a6d8ff', outline='#005599', tags=node_id)
        graph_canvas.create_text(center_x, center_y, text=self.current_person.full_name.split()[0],
                                 font=('Arial', 12, 'bold'), fill='#003366', tags=node_id)

        # Добавляем связанных людей
        relations = list(self.current_person.relations)
        if not relations:
            graph_canvas.create_text(center_x, center_y + 100, text="Нет информации о связях",
                                     font=('Arial', 10), fill='gray')
            return

        angle_step = 360 / len(relations)
        current_angle = 0

        for rel_type, related_person, details in relations:
            # Находим связанного человека (если это объект Person)
            if isinstance(related_person, Person):
                person_obj = related_person
                person_name = related_person.full_name
            else:
                # Ищем человека по имени в нашей базе
                person_obj = None
                person_name = related_person
                for p in self.people.values():
                    if p.full_name == related_person or related_person in p.full_name:
                        person_obj = p
                        break

            # Координаты связанного узла
            rad = math.radians(current_angle)
            node_x = center_x + 250 * math.cos(rad)
            node_y = center_y + 250 * math.sin(rad)

            # ID узла
            if person_obj:
                node_id = f"node_{person_obj.full_name}"
            else:
                node_id = f"node_{person_name}_{current_angle}"

            self.node_positions[node_id] = (node_x, node_y)

            # Цвет узла в зависимости от типа связи
            if 'семь' in rel_type.lower() or 'супруг' in rel_type.lower():
                node_color = '#ffb6c1'  # Розовый для семейных связей
            elif 'работ' in rel_type.lower() or 'коллег' in rel_type.lower():
                node_color = '#98fb98'  # Зеленый для рабочих связей
            elif 'возможн' in rel_type.lower():
                node_color = '#ffa07a'  # Светло-коралловый для возможных связей
            else:
                node_color = '#ffd700'  # Золотой для остальных

            # Рисуем узел связанного человека
            graph_canvas.create_oval(node_x - 60, node_y - 40, node_x + 60, node_y + 40,
                                     fill=node_color, outline='#8b4513', tags=node_id)

            # Имя связанного человека (только фамилия)
            last_name = person_name.split()[0] if ' ' in person_name else person_name
            graph_canvas.create_text(node_x, node_y, text=last_name,
                                     font=('Arial', 10, 'bold'), fill='#8b4513', tags=node_id)

            # Рисуем линию связи
            graph_canvas.create_line(center_x, center_y, node_x, node_y,
                                     arrow=tk.LAST, fill='#666666', width=2)

            # Подпись связи
            label_x = center_x + 125 * math.cos(rad)
            label_y = center_y + 125 * math.sin(rad)

            # Добавляем информацию об источниках и причинах, если есть
            label_text = rel_type
            if details:
                details_text = []
                if 'source_files' in details:
                    details_text.append(f"источники: {len(details['source_files'])}")
                if 'reason' in details:
                    details_text.append(f"причина: {details['reason']}")
                if details_text:
                    label_text += f"\n({'; '.join(details_text)})"

            graph_canvas.create_text(label_x, label_y, text=label_text,
                                     font=('Arial', 8), fill='#333333')

            current_angle += angle_step

    def search_data(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            messagebox.showwarning("Предупреждение", "Введите поисковый запрос")
            return

        self.search_results = []

        # Ищем по всем полям всех людей
        for person in self.people.values():
            # Проверяем имя и алиасы
            if (query in person.full_name.lower() or
                any(query in alias.lower() for alias in person.aliases)):
                self.search_results.append(person)
                continue

            # Проверяем телефоны
            for phone in person.phones:
                if query in phone:
                    self.search_results.append(person)
                    break

            # Проверяем email
            for email in person.emails:
                if query in email.lower():
                    self.search_results.append(person)
                    break

            # Проверяем адреса
            for address in person.addresses:
                if query in address.lower():
                    self.search_results.append(person)
                    break

            # Проверяем автомобили
            for car in person.cars:
                if query in car.lower():
                    self.search_results.append(person)
                    break

            # Проверяем паспорта
            for passport in person.passports:
                if query in passport:
                    self.search_results.append(person)
                    break

            # Проверяем СНИЛС
            if person.snils and query in person.snils:
                self.search_results.append(person)
                continue

            # Проверяем ИНН
            if person.inn and query in person.inn:
                self.search_results.append(person)
                continue

            # Проверяем водительские права
            if person.driver_license and query in person.driver_license:
                self.search_results.append(person)
                continue

            # Проверяем места работы
            for job in person.jobs:
                if query in job.lower():
                    self.search_results.append(person)
                    break

            # Проверяем социальные сети
            for platform, accounts in person.social_media.items():
                for account in accounts:
                    if query in account.lower():
                        self.search_results.append(person)
                        break

            # Проверяем банковские счета
            for account in person.bank_accounts:
                if query in account.lower():
                    self.search_results.append(person)
                    break

            # Проверяем файлы-источники
            for source in person.source_files:
                if query in source.lower():
                    self.search_results.append(person)
                    break

        # Удаляем дубликаты
        self.search_results = list(set(self.search_results))

        # Обновляем список
        self.people_listbox.delete(0, tk.END)
        for person in self.search_results:
            self.people_listbox.insert(tk.END, str(person))

        self.status_bar.config(text=f"Найдено результатов: {len(self.search_results)}")

    def save_data(self):
        if not self.people:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return

        try:
            data_to_save = {
                'people': [person.to_dict() for person in self.people.values()],
                'timestamp': datetime.now().isoformat()
            }

            file_path = filedialog.asksaveasfilename(
                title="Сохранить данные",
                filetypes=(("JSON файлы", "*.json"), ("Все файлы", "*.*")),
                defaultextension=".json"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)

                messagebox.showinfo("Успех", "Данные успешно сохранены!")
                self.status_bar.config(text=f"Данные сохранены в: {file_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении данных:\n{str(e)}")

    def export_to_json(self):
        if not self.people:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return

        try:
            data_to_export = {
                'people': [person.to_dict() for person in self.people.values()],
                'timestamp': datetime.now().isoformat()
            }

            file_path = filedialog.asksaveasfilename(
                title="Экспорт в JSON",
                filetypes=(("JSON файлы", "*.json"), ("Все файлы", "*.*")),
                defaultextension=".json"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_export, f, ensure_ascii=False, indent=2)

                messagebox.showinfo("Успех", "Данные успешно экспортированы в JSON!")
                self.status_bar.config(text=f"Данные экспортированы в: {file_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте данных:\n{str(e)}")

    def export_to_html(self):
        """Экспортирует данные в HTML файл"""
        if not self.people:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return

        try:
            file_path = filedialog.asksaveasfilename(
                title="Экспорт в HTML",
                filetypes=(("HTML файлы", "*.html"), ("Все файлы", "*.*")),
                defaultextension=".html"
            )

            if not file_path:
                return

            with open(file_path, 'w', encoding='utf-8') as f:
                # HTML заголовок
                f.write('<!DOCTYPE html>\n<html lang="ru">\n<head>\n')
                f.write('<meta charset="UTF-8">\n')
                f.write('<title>Экспорт данных о людях</title>\n')
                f.write('<style>\n')
                f.write('body { font-family: Arial, sans-serif; margin: 20px; }\n')
                f.write('h1 { color: #333; }\n')
                f.write('.person { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }\n')
                f.write('.person h2 { margin-top: 0; color: #005599; }\n')
                f.write('.section { margin-bottom: 15px; }\n')
                f.write('.section h3 { margin-bottom: 5px; color: #555; }\n')
                f.write('.item { margin-left: 20px; margin-bottom: 3px; }\n')
                f.write('.relation { background-color: #f5f5f5; padding: 8px; border-radius: 3px; margin-bottom: 5px; }\n')
                f.write('</style>\n')
                f.write('</head>\n<body>\n')
                f.write(f'<h1>Экспорт данных о людях</h1>\n')
                f.write(f'<p>Всего людей: {len(self.people)}</p>\n')
                f.write(f'<p>Дата экспорта: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>\n')

                # Данные каждого человека
                for person in sorted(self.people.values(), key=lambda p: p.full_name):
                    f.write(f'<div class="person">\n')
                    f.write(f'<h2>{escape(person.full_name)}</h2>\n')

                    # Основная информация
                    f.write('<div class="section">\n')
                    f.write('<h3>Основная информация</h3>\n')
                    if person.birth_date:
                        f.write(f'<div class="item">Дата рождения: {escape(person.birth_date)}</div>\n')
                    if person.snils:
                        f.write(f'<div class="item">СНИЛС: {escape(person.snils)}</div>\n')
                    if person.inn:
                        f.write(f'<div class="item">ИНН: {escape(person.inn)}</div>\n')
                    if person.driver_license:
                        f.write(f'<div class="item">Водительское удостоверение: {escape(person.driver_license)}</div>\n')
                    if person.source_files:
                        files = ", ".join(escape(f) for f in person.source_files)
                        f.write(f'<div class="item">Источники данных: {files}</div>\n')
                    if person.aliases:
                        aliases = ", ".join(escape(a) for a in person.aliases)
                        f.write(f'<div class="item">Другие варианты имени: {aliases}</div>\n')
                    f.write('</div>\n')

                    # Контактные данные
                    if person.phones or person.emails or person.addresses:
                        f.write('<div class="section">\n')
                        f.write('<h3>Контактные данные</h3>\n')
                        if person.phones:
                            f.write('<div class="item">Телефоны:</div>\n')
                            for phone in person.phones:
                                f.write(f'<div class="item" style="margin-left:40px;">{escape(phone)}</div>\n')
                        if person.emails:
                            f.write('<div class="item">Email:</div>\n')
                            for email in person.emails:
                                f.write(f'<div class="item" style="margin-left:40px;">{escape(email)}</div>\n')
                        if person.addresses:
                            f.write('<div class="item">Адреса:</div>\n')
                            for address in person.addresses:
                                f.write(f'<div class="item" style="margin-left:40px;">{escape(address)}</div>\n')
                        f.write('</div>\n')

                    # Документы
                    if person.passports:
                        f.write('<div class="section">\n')
                        f.write('<h3>Документы</h3>\n')
                        f.write('<div class="item">Паспорта:</div>\n')
                        for passport in person.passports:
                            f.write(f'<div class="item" style="margin-left:40px;">{escape(passport)}</div>\n')
                        f.write('</div>\n')

                    # Транспорт
                    if person.cars:
                        f.write('<div class="section">\n')
                        f.write('<h3>Транспорт</h3>\n')
                        f.write('<div class="item">Автомобили:</div>\n')
                        for car in person.cars:
                            f.write(f'<div class="item" style="margin-left:40px;">{escape(car)}</div>\n')
                        f.write('</div>\n')

                    # Финансы
                    if person.bank_accounts:
                        f.write('<div class="section">\n')
                        f.write('<h3>Финансы</h3>\n')
                        f.write('<div class="item">Банковские счета:</div>\n')
                        for account in person.bank_accounts:
                            f.write(f'<div class="item" style="margin-left:40px;">{escape(account)}</div>\n')
                        f.write('</div>\n')

                    # Социальные сети
                    if any(person.social_media.values()):
                        f.write('<div class="section">\n')
                        f.write('<h3>Социальные сети</h3>\n')
                        for platform, accounts in person.social_media.items():
                            if accounts:
                                f.write(f'<div class="item">{platform.upper()}:</div>\n')
                                for account in accounts:
                                    f.write(f'<div class="item" style="margin-left:40px;"><a href="{escape(account)}" target="_blank">{escape(account)}</a></div>\n')
                        f.write('</div>\n')

                    # Работа
                    if person.jobs:
                        f.write('<div class="section">\n')
                        f.write('<h3>Работа</h3>\n')
                        f.write('<div class="item">Места работы:</div>\n')
                        for job in person.jobs:
                            f.write(f'<div class="item" style="margin-left:40px;">{escape(job)}</div>\n')
                        f.write('</div>\n')

                    # Связи
                    if person.relations:
                        f.write('<div class="section">\n')
                        f.write('<h3>Связи</h3>\n')
                        for rel_type, related_person, frozen_details in person.relations:
                            details = dict(frozen_details)
                            if isinstance(related_person, Person):
                                rel_text = f"{rel_type}: {related_person.full_name}"
                            else:
                                rel_text = f"{rel_type}: {related_person}"

                            if details:
                                details_text = []
                                if 'source_files' in details:
                                    details_text.append(f"источники: {len(details['source_files'])}")
                                if 'reason' in details:
                                    details_text.append(f"причина: {details['reason']}")
                                if details_text:
                                    rel_text += f" ({'; '.join(details_text)})"

                            f.write(f'<div class="relation">{escape(rel_text)}</div>\n')
                        f.write('</div>\n')

                    f.write('</div>\n')

                # Закрываем HTML
                f.write('</body>\n</html>')

            messagebox.showinfo("Успех", "Данные успешно экспортированы в HTML!")
            self.status_bar.config(text=f"Данные экспортированы в: {file_path}")

            # Открываем файл в браузере
            webbrowser.open(f'file://{os.path.abspath(file_path)}')

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте в HTML:\n{str(e)}")

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Открыть файл с данными",
            filetypes=(("Текстовые файлы", "*.txt"), ("Все файлы", "*.*"))
        )

        if file_path:
            self.file_path = file_path
            self.load_data()

    def load_data(self):
        if not self.file_path:
            messagebox.showwarning("Предупреждение", "Сначала выберите файл")
            return

        try:
            self.current_file_people = set()  # Сбрасываем список людей для текущего файла
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            filename = os.path.basename(self.file_path)
            self.parse_data(content, source_file=filename)

            # Создаем связи между всеми людьми из этого файла
            self.create_relations_within_file()

            self.update_people_list()
            self.status_bar.config(text=f"Загружено: {self.file_path} | Людей: {len(self.people)}")
            messagebox.showinfo("Успех", "Данные успешно загружены и обработаны!")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке файла:\n{str(e)}")

    def clear_canvas(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.graph_objects = []
        self.node_positions = {}
        self.selected_node = None

    def copy_to_clipboard(self, text):
        """Копирует текст в буфер обмена"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_bar.config(text=f"Скопировано: {text[:30]}..." if len(text) > 30 else f"Скопировано: {text}")


if __name__ == "__main__":
    root = tk.Tk()
    app = DataVisualizer(root)
    root.mainloop()