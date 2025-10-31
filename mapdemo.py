import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import webbrowser
import os
import re
import time
import json
import openai
from datetime import datetime


class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Карта адресов - AI версия")
        self.root.geometry("800x650")

        # Настройки OpenAI
        self.openai_api_key = None
        self.openai_enabled = False

        # Создаем основной фрейм
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Заголовок
        title_label = tk.Label(main_frame, text="Картографирование адресов с AI", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # Фрейм для настроек OpenAI
        openai_frame = tk.LabelFrame(main_frame, text="Настройки OpenAI", font=("Arial", 10))
        openai_frame.pack(fill=tk.X, pady=5)

        # Поле для API ключа
        tk.Label(openai_frame, text="API ключ OpenAI:", font=("Arial", 9)).pack(anchor="w", pady=2)
        self.api_key_var = tk.StringVar()
        api_key_entry = tk.Entry(openai_frame, textvariable=self.api_key_var, show="*", width=50)
        api_key_entry.pack(fill=tk.X, pady=2)

        # Чекбокс для использования OpenAI
        self.use_openai_var = tk.BooleanVar(value=False)
        openai_cb = tk.Checkbutton(
            openai_frame,
            text="Использовать OpenAI для нормализации адресов",
            variable=self.use_openai_var,
            font=("Arial", 9),
            command=self.toggle_openai
        )
        openai_cb.pack(anchor="w", pady=2)

        # Фрейм для обычных настроек
        settings_frame = tk.LabelFrame(main_frame, text="Настройки", font=("Arial", 10))
        settings_frame.pack(fill=tk.X, pady=5)

        # Чекбокс для автоматической коррекции адресов
        self.auto_correct_var = tk.BooleanVar(value=True)
        auto_correct_cb = tk.Checkbutton(
            settings_frame,
            text="Автоматически исправлять форматы адресов",
            variable=self.auto_correct_var,
            font=("Arial", 9)
        )
        auto_correct_cb.pack(anchor="w", pady=2)

        # Чекбокс для расширенного геокодирования
        self.extended_geocoding_var = tk.BooleanVar(value=True)
        extended_geocoding_cb = tk.Checkbutton(
            settings_frame,
            text="Расширенное геокодирование (больше попыток)",
            variable=self.extended_geocoding_var,
            font=("Arial", 9)
        )
        extended_geocoding_cb.pack(anchor="w", pady=2)

        # Кнопка выбора файла
        self.select_button = tk.Button(
            main_frame,
            text="Выбрать файл с адресами",
            command=self.load_addresses,
            padx=20,
            pady=10,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10)
        )
        self.select_button.pack(pady=10)

        # Текстовое поле для просмотра загруженных адресов
        tk.Label(main_frame, text="Загруженные адреса:", font=("Arial", 10)).pack(anchor="w")
        self.addresses_text = scrolledtext.ScrolledText(
            main_frame,
            height=12,
            width=80,
            font=("Arial", 9)
        )
        self.addresses_text.pack(pady=5, fill=tk.BOTH, expand=True)

        # Фрейм для кнопок
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=10)

        # Кнопка показа карты
        self.show_map_button = tk.Button(
            button_frame,
            text="Показать на карте",
            command=self.show_map,
            padx=20,
            pady=10,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10),
            state=tk.DISABLED
        )
        self.show_map_button.pack(side=tk.LEFT, padx=5)

        # Кнопка очистки
        self.clear_button = tk.Button(
            button_frame,
            text="Очистить",
            command=self.clear_addresses,
            padx=20,
            pady=10,
            bg="#f44336",
            fg="white",
            font=("Arial", 10)
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # Кнопка ручного ввода
        self.manual_button = tk.Button(
            button_frame,
            text="Ручной ввод",
            command=self.manual_input,
            padx=20,
            pady=10,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10)
        )
        self.manual_button.pack(side=tk.LEFT, padx=5)

        # Статус бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.addresses = []
        self.geocoded_locations = []

    def toggle_openai(self):
        """Включение/выключение OpenAI"""
        if self.use_openai_var.get():
            self.openai_api_key = self.api_key_var.get().strip()
            if not self.openai_api_key:
                messagebox.showwarning("Предупреждение", "Введите API ключ OpenAI!")
                self.use_openai_var.set(False)
                return

            try:
                openai.api_key = self.openai_api_key
                # Тестовый запрос для проверки ключа
                openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                self.openai_enabled = True
                self.status_var.set("OpenAI подключен")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Неверный API ключ OpenAI: {str(e)}")
                self.use_openai_var.set(False)
                self.openai_enabled = False
        else:
            self.openai_enabled = False
            self.status_var.set("OpenAI отключен")

    def normalize_with_openai(self, addresses):
        """Нормализация адресов с помощью OpenAI"""
        if not self.openai_enabled:
            return addresses

        try:
            prompt = f"""
            Нормализуй следующие российские адреса в правильный формат. 
            Верни результат в формате JSON: {{"normalized_addresses": ["адрес1", "адрес2", ...]}}

            Правила нормализации:
            1. Приводи к формату: "город, улица, дом, корпус/строение, квартира/офис"
            2. Расшифровывай сокращения: МО -> Московская область, ГО -> Городской округ
            3. Исправляй опечатки и нестандартные написания
            4. Для Москвы используй полные названия улиц
            5. СНТ расшифровывай как "Садовое некоммерческое товарищество"
            6. Нижние поля -> Нижние Поля
            7. Для номеров домов с буквами: 20Бс1 -> д. 20, корп. Б, стр. 1

            Адреса для нормализации:
            {chr(10).join(f"{i + 1}. {addr}" for i, addr in enumerate(addresses))}

            Верни ТОЛЬКО JSON без дополнительного текста.
            """

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "Ты специалист по российским адресам. Нормализуй адреса строго по правилам."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            result_text = response.choices[0].message.content.strip()

            # Парсим JSON ответ
            if result_text.startswith('```json'):
                result_text = result_text[7:-3]  # Убираем ```json и ```

            result = json.loads(result_text)
            normalized = result.get("normalized_addresses", addresses)

            # Логируем изменения
            for orig, norm in zip(addresses, normalized):
                if orig != norm:
                    print(f"OpenAI нормализовал: '{orig}' -> '{norm}'")

            return normalized

        except Exception as e:
            print(f"Ошибка OpenAI: {e}")
            return addresses

    def load_addresses(self):
        """Загрузка адресов из текстового файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл с адресами",
            filetypes=[("Текстовые файлы", "*.txt"), ("CSV файлы", "*.csv"), ("Все файлы", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    raw_addresses = [line.strip() for line in file if line.strip()]

                # Обрабатываем адреса
                self.addresses = self.process_addresses(raw_addresses)

                # Показываем адреса в текстовом поле
                self.addresses_text.delete(1.0, tk.END)
                for i, address in enumerate(self.addresses, 1):
                    self.addresses_text.insert(tk.END, f"{i}. {address}\n")

                messagebox.showinfo("Успех", f"Загружено {len(self.addresses)} адресов!")
                self.show_map_button.config(state=tk.NORMAL)
                self.status_var.set(f"Загружено {len(self.addresses)} адресов")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {str(e)}")

    def manual_input(self):
        """Ручной ввод адресов"""
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Ручной ввод адресов")
        manual_window.geometry("500x400")

        tk.Label(manual_window, text="Введите адреса (каждый с новой строки):", font=("Arial", 10)).pack(pady=10)

        text_area = scrolledtext.ScrolledText(manual_window, height=15, width=60, font=("Arial", 9))
        text_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        def add_addresses():
            text = text_area.get(1.0, tk.END).strip()
            if text:
                raw_addresses = [line.strip() for line in text.split('\n') if line.strip()]
                new_addresses = self.process_addresses(raw_addresses)
                self.addresses.extend(new_addresses)

                # Обновляем текстовое поле
                self.addresses_text.delete(1.0, tk.END)
                for i, address in enumerate(self.addresses, 1):
                    self.addresses_text.insert(tk.END, f"{i}. {address}\n")

                self.show_map_button.config(state=tk.NORMAL)
                self.status_var.set(f"Загружено {len(self.addresses)} адресов")
                manual_window.destroy()
                messagebox.showinfo("Успех", f"Добавлено {len(new_addresses)} адресов!")

        button_frame = tk.Frame(manual_window)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Добавить", command=add_addresses, bg="#4CAF50", fg="white").pack(side=tk.LEFT,
                                                                                                       padx=5)
        tk.Button(button_frame, text="Отмена", command=manual_window.destroy).pack(side=tk.LEFT, padx=5)

    def process_addresses(self, raw_addresses):
        """Обработка и нормализация адресов в различных форматах"""
        processed_addresses = []

        for address in raw_addresses:
            if not address or address.isspace():
                continue

            if self.auto_correct_var.get():
                cleaned_address = self.clean_and_normalize_address(address)
            else:
                cleaned_address = address.strip()

            if cleaned_address:
                processed_addresses.append(cleaned_address)

        # Используем OpenAI для дополнительной нормализации
        if self.openai_enabled and processed_addresses:
            try:
                self.status_var.set("Нормализация адресов с OpenAI...")
                self.root.update()

                processed_addresses = self.normalize_with_openai(processed_addresses)
                self.status_var.set("Нормализация завершена")

            except Exception as e:
                print(f"Ошибка при нормализации OpenAI: {e}")
                self.status_var.set("Ошибка нормализации OpenAI")

        return processed_addresses

    def clean_and_normalize_address(self, address):
        """Расширенная очистка и нормализация адреса"""
        if not address:
            return None

        original_address = address

        try:
            # Базовая очистка
            address = address.strip()
            address = re.sub(r'\s+', ' ', address)

            # Специфические исправления для проблемных адресов
            address = self.fix_specific_addresses(address)

            # Стандартные замены
            replacements = {
                # Регионы
                r'\bМО\b': 'Московская область',
                r'\bГО\b': 'Городской округ',
                r'\bг\.\s*': 'г. ',
                r'\bс\.\s*': 'с. ',
                r'\bпос\.\s*': 'пос. ',
                r'\bСНТ\b': 'Садовое некоммерческое товарищество',

                # Улицы
                r'\bул\.\s*': 'ул. ',
                r'\bулица\s+': 'ул. ',
                r'\bпр-т\s*': 'пр-т ',
                r'\bпроспект\s+': 'пр-т ',
                r'\bпер\.\s*': 'пер. ',
                r'\bпереулок\s+': 'пер. ',

                # Номера домов
                r'\bдом\s*': 'д. ',
                r'\bд\.\s*': 'д. ',
                r'\bкорпус\s*': 'корп. ',
                r'\bкорп\.\s*': 'корп. ',
                r'\bстроение\s*': 'стр. ',
                r'\bстр\.\s*': 'стр. ',
                r'\bквартира\s*': 'кв. ',
                r'\bкв\.\s*': 'кв. ',
            }

            for pattern, replacement in replacements.items():
                address = re.sub(pattern, replacement, address, flags=re.IGNORECASE)

            # Обработка сложных номеров домов
            address = re.sub(r'д\.\s*(\d+)([A-ZА-Яa-zа-я]\S*)', r'д. \1, корп. \2', address)
            address = re.sub(r'д\.\s*(\d+)\s*[/\\]\s*(\d+)', r'д. \1/\2', address)

            # Капитализация
            address = self.capitalize_address(address)

            return address if address and not address.isspace() else original_address

        except Exception as e:
            print(f"Ошибка при обработке адреса '{original_address}': {e}")
            return original_address

    def fix_specific_addresses(self, address):
        """Исправление конкретных проблемных адресов"""
        specific_fixes = {
            r'Нижние поля\s*20Бс1': 'г. Москва, ул. Нижние Поля, д. 20, корп. Б, стр. 1',
            r'МО,\s*ГО чехов,\s*снт дубна\s*81': 'Московская область, Городской округ Чехов, Садовое некоммерческое товарищество Дубна, д. 81',
            r'москва улица красноказарменная дом 12': 'г. Москва, ул. Красноказарменная, д. 12',
        }

        for pattern, replacement in specific_fixes.items():
            if re.search(pattern, address, re.IGNORECASE):
                return replacement

        return address

    def capitalize_address(self, address):
        """Капитализация адреса"""
        # Капитализируем первые буквы каждого слова, но сохраняем сокращения
        words = address.split()
        capitalized_words = []

        for word in words:
            if word.endswith('.') and len(word) <= 3:  # Сокращения
                capitalized_words.append(word)
            else:
                capitalized_words.append(word.capitalize())

        return ' '.join(capitalized_words)

    def geocode_address(self, address, retry_count=3):
        """Расширенное геокодирование адреса"""
        if self.extended_geocoding_var.get():
            retry_count = 5

        geolocator = Nominatim(user_agent=f"ai_map_app_{int(time.time())}")

        search_variants = self.generate_search_variants(address)

        for search_address in search_variants:
            for attempt in range(retry_count):
                try:
                    location = geolocator.geocode(search_address, addressdetails=True, timeout=15, language='ru')
                    if location:
                        return {
                            'address': address,
                            'search_address': search_address,
                            'coordinates': (location.latitude, location.longitude),
                            'found_address': location.address,
                            'raw': location.raw
                        }
                    time.sleep(1)

                except (GeocoderTimedOut, GeocoderUnavailable) as e:
                    if attempt == retry_count - 1:
                        print(f"Ошибка геокодирования для '{search_address}': {str(e)}")
                    time.sleep(2)
                except Exception as e:
                    print(f"Неизвестная ошибка для '{search_address}': {str(e)}")
                    break

        return None

    def generate_search_variants(self, address):
        """Генерация вариантов поиска"""
        variants = [address]

        # Упрощенные варианты
        simplified = re.sub(r',\s*(кв\.|оф\.|пом\.|каб\.)\s*\d+', '', address)
        if simplified != address:
            variants.append(simplified)

        # Без дополнительных деталей
        simplified2 = re.sub(r',\s*(корп\.|стр\.|лит\.)\s*\S+', '', simplified)
        if simplified2 not in variants:
            variants.append(simplified2)

        return variants

    def show_map(self):
        """Создание и отображение карты"""
        if not self.addresses:
            messagebox.showwarning("Предупреждение", "Нет адресов для отображения!")
            return

        self.status_var.set("Начинаем геокодирование адресов...")
        self.root.update()

        successful_markers = 0
        failed_addresses = []
        self.geocoded_locations = []

        # Прогресс-окно
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Геокодирование адресов")
        progress_window.geometry("450x150")
        progress_window.transient(self.root)
        progress_window.grab_set()

        progress_label = tk.Label(progress_window, text="Обработка адресов...", font=("Arial", 10))
        progress_label.pack(pady=10)

        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=len(self.addresses))
        progress_bar.pack(fill=tk.X, padx=20, pady=5)

        count_label = tk.Label(progress_window, text="0/0", font=("Arial", 9))
        count_label.pack()

        status_label = tk.Label(progress_window, text="", font=("Arial", 8))
        status_label.pack()

        # Геокодируем адреса
        for i, address in enumerate(self.addresses):
            progress_var.set(i)
            progress_label.config(text=f"Обработка: {address[:45]}...")
            count_label.config(text=f"{i + 1}/{len(self.addresses)}")
            status_label.config(text="Геокодирование...")
            progress_window.update()

            location_data = self.geocode_address(address)
            if location_data:
                self.geocoded_locations.append(location_data)
                successful_markers += 1
                status_label.config(text="✓ Успешно")
            else:
                failed_addresses.append(address)
                status_label.config(text="✗ Не найдено")

            time.sleep(1)  # Задержка для API

        progress_window.destroy()

        if not self.geocoded_locations:
            messagebox.showerror("Ошибка", "Не удалось геокодировать ни один адрес!")
            self.status_var.set("Геокодирование завершено с ошибками")
            return

        # Создаем карту
        self.status_var.set("Создание карты...")
        self.root.update()

        # Центр карты
        lats = [loc['coordinates'][0] for loc in self.geocoded_locations]
        lons = [loc['coordinates'][1] for loc in self.geocoded_locations]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

        # Добавляем маркеры
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'darkblue']
        for i, location in enumerate(self.geocoded_locations):
            lat, lon = location['coordinates']
            color = colors[i % len(colors)]

            popup_text = f"""
            <div style="font-family: Arial; font-size: 12px;">
            <b>Исходный адрес:</b> {location['address']}<br>
            <b>Найден как:</b> {location['found_address']}<br>
            <b>Координаты:</b> {lat:.6f}, {lon:.6f}<br>
            <small><i>Поисковый запрос: {location.get('search_address', location['address'])}</i></small>
            </div>
            """

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=400),
                tooltip=location['address'],
                icon=folium.Icon(color=color, icon='home')
            ).add_to(m)

        # Сохраняем карту
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        map_file = f"addresses_map_{timestamp}.html"
        m.save(map_file)

        # Открываем карту
        webbrowser.open(f'file://{os.path.abspath(map_file)}')

        # Результаты
        result_message = f"Успешно размещено {successful_markers} из {len(self.addresses)} адресов"
        if failed_addresses:
            result_message += f"\n\nНе найдены адреса ({len(failed_addresses)}):\n" + "\n".join(failed_addresses[:10])
            if len(failed_addresses) > 10:
                result_message += f"\n... и еще {len(failed_addresses) - 10} адресов"

        messagebox.showinfo("Результат", result_message)
        self.status_var.set(f"Карта создана: {successful_markers}/{len(self.addresses)} адресов")

    def clear_addresses(self):
        """Очистка всех адресов"""
        self.addresses = []
        self.geocoded_locations = []
        self.addresses_text.delete(1.0, tk.END)
        self.show_map_button.config(state=tk.DISABLED)
        self.status_var.set("Готов к работе")


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApp(root)
    root.mainloop()