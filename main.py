import requests
import pandas as pd
from utils.data_manager import DataManager
from utils.taxonomy_translator import TaxonomyTranslator
import time
from utils.russian_animals_db import RussianAnimalsDB
import sys
import time
from tqdm import tqdm

class AnimalFinder:
    def __init__(self):
        self.data_manager = DataManager()
        self.translator = TaxonomyTranslator()
        self.animals_db = RussianAnimalsDB()
        self.common_name_cache = {}
        self.region_translations = {
            'Амурская': 'Amur',
            'Московская': 'Moscow',
            'Ленинградская': 'Leningrad',
            'Краснодарская': 'Krasnodar',
            'Новосибирская': 'Novosibirsk',
            'Брянская': 'Bryansk',
            'Нижегородская': 'Nizhny Novgorod',
            'Татарстан': 'Tatarstan'
        }

    def get_region_by_coordinates(self, latitude, longitude):
        """Определяет регион по координатам"""
        return self.data_manager.get_region_by_coordinates(latitude, longitude)
    2
    def show_regions_statistics(self):
        """Показывает статистику по сохраненным регионам"""
        print("\n📊 СОХРАНЕННЫЕ ДАННЫЕ ПО РЕГИОНАМ:")
        print("=" * 60)

        # Получаем все регионы из файла ключей
        all_regions = self.data_manager.get_all_regions()

        if not all_regions:
            print("❌ Нет сохраненных данных о регионах")
            return

        print(f"{'Регион':<25} {'Всего':<6} {'Видов':<6} {'Распределение по классам'}")
        print("-" * 60)

        for region_en, region_info in all_regions.items():
            # Получаем данные региона
            region_data = self.data_manager.get_region_data(region_en)

            if region_data:
                df = pd.DataFrame(region_data)
                region_name = region_info.get('name_ru', region_en)
                total = len(region_data)
                species = df['scientific_name'].nunique()

                # Статистика по классам - безопасный подход
                class_stats = {}
                for animal in region_data:
                    # Используем class_ru если есть, иначе обычный class
                    animal_class = animal.get('class_ru')
                    if not animal_class or animal_class == 'Не указано':
                        animal_class = animal.get('class', 'Не указано')

                    if animal_class and animal_class != 'Не указано':
                        class_stats[animal_class] = class_stats.get(animal_class, 0) + 1

                # Формируем строку распределения по классам
                class_dist = []
                for class_name, count in list(class_stats.items())[:3]:  # Показываем топ-3
                    short_name = class_name[:12] + '..' if len(class_name) > 12 else class_name
                    class_dist.append(f"{short_name}:{count}")

                distribution_str = ", ".join(class_dist)
                if len(class_stats) > 3:
                    distribution_str += " ..."

                print(f"{region_name:<25} {total:<6} {species:<6} {distribution_str}")
            else:
                print(f"{region_info.get('name_ru', region_en):<25} {'-':<6} {'-':<6} нет данных")

    def get_available_regions_list(self):
        """Получает список регионов, которые можно использовать"""
        all_regions = self.data_manager.get_all_regions()

        if all_regions:
            available = []
            for region_en, region_info in all_regions.items():
                region_data = self.data_manager.get_region_data(region_en)
                if region_data and len(region_data) > 0:
                    available.append(region_info.get('name_ru', region_en))
            return available
        else:
            # Возвращаем регионы, которые мы знаем что работают
            return ["Krasnodar", "Moscow", "Tatarstan", "Amur", "Bryansk", "Nizhny Novgorod"]

    def _get_russian_common_name_cached(self, species_key):
        """Получает русское название вида с кэшированием"""
        if not species_key:
            return 'Не указано'

        if species_key in self.common_name_cache:
            return self.common_name_cache[species_key]

        common_name = self._get_russian_common_name(species_key)
        self.common_name_cache[species_key] = common_name
        return common_name

    def analyze_region_improved(self, region_name_ru):
        """Улучшенный анализ региона с группировкой по классам и фильтрацией"""
        animals = self.get_animals_by_region(region_name_ru)

        if not animals:
            print(f"❌ Нет данных для региона {region_name_ru}")
            return

        # ПРИМЕНЯЕМ ФИЛЬТРАЦИЮ ДО АНАЛИЗА
        filtered_animals = self.filter_animals_data(animals, min_count=2)

        if not filtered_animals:
            print(f"🎯 После фильтрации не осталось значимых данных для региона {region_name_ru}")
            return

        df = pd.DataFrame(filtered_animals)

        print(f"\n{'=' * 60}")
        print(f"🐾 АНАЛИЗ ЖИВОТНЫХ В {region_name_ru.upper()} ОБЛАСТИ")
        print(f"{'=' * 60}")

        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"Всего находок: {len(filtered_animals)}")
        print(f"Уникальных видов: {df['scientific_name'].nunique()}")

        # Группировка по классам с перечислением видов - безопасный подход
        class_groups = {}
        for animal in filtered_animals:  # ИСПОЛЬЗУЕМ ОТФИЛЬТРОВАННЫЕ ДАННЫЕ
            # Используем class_ru если есть, иначе обычный class
            class_name = animal.get('class_ru')
            if not class_name or class_name == 'Не указано':
                class_name = animal.get('class', 'Не указано')

            if class_name not in class_groups:
                class_groups[class_name] = []
            class_groups[class_name].append(animal)

        # Показываем только значимые классы
        significant_classes = 0
        for class_name, group_animals in class_groups.items():
            if class_name and class_name != 'Не указано' and len(group_animals) >= 2:  # Минимум 2 животные в классе
                class_count = len(group_animals)
                percentage = (class_count / len(filtered_animals)) * 100

                # Пропускаем неинтересные классы
                if class_name in ['Насекомые', 'Паукообразные', 'Диплоподы', 'Губки']:
                    continue

                print(f"\n📈 {class_name.upper()} - {class_count} ({percentage:.1f}%):")
                significant_classes += 1

                # Топ видов в этом классе
                species_counts = {}
                for animal in group_animals:
                    species = animal['scientific_name']
                    species_counts[species] = species_counts.get(species, 0) + 1

                top_species = sorted(species_counts.items(), key=lambda x: x[1], reverse=True)[:5]

                for i, (species, count) in enumerate(top_species, 1):
                    # Находим common_name для этого вида
                    common_name = next(
                        (a.get('common_name', 'Не указано') for a in group_animals if a['scientific_name'] == species),
                        'Не указано')
                    display_name = common_name if common_name != 'Не указано' else species
                    print(f"   {i}. {display_name} - {count} находок")

        if significant_classes == 0:
            print("🎯 Нет значимых классов животных для показа")

    def show_detailed_animal_info_improved(self, animals, count=8):
        """Улучшенный вывод детальной информации о животных с фильтрацией"""
        # ФИЛЬТРУЕМ данные перед показом
        filtered_animals = self.filter_animals_data(animals, min_count=1)  # Минимум 1 находка для показа

        if not filtered_animals:
            print("🎯 После фильтрации не осталось значимых животных для показа")
            return

        display_count = min(count, len(filtered_animals))
        print(f"\n🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О {display_count} ЖИВОТНЫХ:")

        for i, animal in enumerate(filtered_animals[:display_count], 1):
            # Используем научное название, если нет русского
            display_name = animal.get('common_name', 'Не указано')
            if display_name == 'Не указано':
                display_name = animal['scientific_name']

            print(f"\n{i}. {display_name}")
            print(f"   Научное название: {animal['scientific_name']}")

            # Выводим таксономию на русском - безопасный подход
            taxon_info = []

            # Тип
            phylum = animal.get('phylum_ru', animal.get('phylum', 'Не указано'))
            if phylum != 'Не указано':
                taxon_info.append(f"Тип: {phylum}")

            # Класс
            animal_class = animal.get('class_ru', animal.get('class', 'Не указано'))
            if animal_class != 'Не указано':
                taxon_info.append(f"Класс: {animal_class}")

            # Отряд
            order = animal.get('order_ru', animal.get('order', 'Не указано'))
            if order != 'Не указано':
                taxon_info.append(f"Отряд: {order}")

            # Семейство
            family = animal.get('family_ru', animal.get('family', 'Не указано'))
            if family != 'Не указано':
                taxon_info.append(f"Семейство: {family}")

            if taxon_info:
                print(f"   {' | '.join(taxon_info)}")

            # Источник данных
            source = animal.get('source', 'GBIF')
            if source == 'local_db':
                print(f"   📚 Источник: база данных")
            else:
                print(f"   🌐 Источник: GBIF")

            # Дополнительная информация (только если есть)
            if animal.get('locality') and animal['locality'] != 'Не указано':
                print(f"   📍 Место: {animal['locality']}")
            if animal.get('eventDate') and animal['eventDate'] != 'Не указано':
                # Обрезаем время, если есть
                date_str = animal['eventDate'].split('T')[0] if 'T' in animal['eventDate'] else animal['eventDate']
                print(f"   📅 Дата: {date_str}")

    def get_animals_by_coordinates(self, latitude, longitude, force_update=False):
        """Получает животных по координатам - пробуем оба метода"""
        print(f"📍 Поиск животных для координат: {latitude}, {longitude}")

        # Сначала пробуем через определение региона
        region_ru, region_en = self.get_region_by_coordinates(latitude, longitude)
        animals_by_region = self.get_animals_by_region(region_ru, force_update)

        if animals_by_region:
            print(f"✅ Найдено {len(animals_by_region)} животных через регион '{region_ru}'")
            return animals_by_region
        else:
            print(f"❌ Через регион '{region_ru}' не найдено животных, пробуем прямой поиск...")
            # Пробуем прямой поиск по координатам
            animals_direct = self.get_animals_by_coordinates_direct(latitude, longitude)

            if animals_direct:
                print(f"✅ Прямой поиск нашел {len(animals_direct)} животных")
                # Сохраняем найденных животных под регионом
                if region_ru != "Неизвестный регион":
                    self.data_manager.save_region_data(region_en, region_ru, animals_direct)
                return animals_direct
            else:
                print("❌ Оба метода не дали результатов")
                return []

    def check_available_regions(self):
        """Показывает регионы, для которых есть данные о ЖИВОТНЫХ"""
        print("\n🗺️ РЕГИОНЫ С ДАННЫМИ О ЖИВОТНЫХ В GBIF:")
        print("=" * 50)

        test_regions = [
            ('Amur', 'Амурская'),
            ('Moscow', 'Московская'),
            ('Moscow Oblast', 'Московская обл.'),
            ('Krasnodar', 'Краснодарская'),
            ('Leningrad', 'Ленинградская'),
            ('Saint Petersburg', 'Санкт-Петербург'),
            ('Novosibirsk', 'Новосибирская'),
            ('Khabarovsk', 'Хабаровский'),
            ('Primorsky', 'Приморский'),
            ('Sverdlovsk', 'Свердловская'),
            ('Rostov', 'Ростовская'),
            ('Chelyabinsk', 'Челябинская'),
            ('Irkutsk', 'Иркутская'),
            ('Tatarstan', 'Татарстан'),
            ('Bashkortostan', 'Башкортостан'),
            ('Crimea', 'Крым')
        ]

        animal_regions = []

        for region_en, region_ru in test_regions:
            base_url = "https://api.gbif.org/v1"

            # Более строгие параметры для животных
            params = {
                'country': 'RU',
                'stateProvince': region_en,
                'kingdom': 'Animalia',
                'hasCoordinate': 'true',  # Только с координатами
                'limit': 10
            }

            try:
                response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data['count'] > 0:
                        # Проверим что это действительно животные
                        animal_count = 0
                        for record in data.get('results', [])[:5]:
                            kingdom = record.get('kingdom', '').lower()
                            if kingdom == 'animalia':
                                animal_count += 1

                        status = "✅ ЖИВОТНЫЕ" if animal_count > 0 else "❌ НЕТ ЖИВОТНЫХ"
                        animal_regions.append((region_ru, region_en, data['count'], animal_count))
                        print(
                            f"{region_ru:20} {region_en:20} {data['count']:6} зап. {animal_count}/5 животных {status}")
                    else:
                        print(f"{region_ru:20} {region_en:20} {'-':6} зап. ❌ НЕТ ДАННЫХ")
                else:
                    print(f"{region_ru:20} {region_en:20} ОШИБКА API: {response.status_code}")
            except Exception as e:
                print(f"{region_ru:20} {region_en:20} ОШИБКА: {e}")

        print(f"\n🎯 РЕКОМЕНДУЕМЫЕ РЕГИОНЫ С ЖИВОТНЫМИ:")
        for region_ru, region_en, total, animals in animal_regions:
            if animals > 0:
                print(f"   • {region_ru} ({region_en}) - {total} записей")

        return animal_regions

    def _fetch_from_api(self, region_name_en, region_name_ru):
        """Получает данные через GBIF API - с принудительной фильтрацией животных"""
        base_url = "https://api.gbif.org/v1"

        # Улучшенные параметры запроса с принудительной фильтрацией
        params_list = [
            # Запрос 1: Только основные классы животных
            {
                'country': 'RU',
                'stateProvince': region_name_en,
                'class': 'Mammalia,Aves,Reptilia,Amphibia,Insecta,Arachnida,Actinopterygii',
                'hasCoordinate': 'true',
                'basisOfRecord': 'HUMAN_OBSERVATION,OBSERVATION',
                'limit': 2000
            },
            # Запрос 2: Только животные с наблюдениями
            {
                'country': 'RU',
                'stateProvince': region_name_en,
                'kingdom': 'Animalia',
                'hasCoordinate': 'true',
                'basisOfRecord': 'HUMAN_OBSERVATION,OBSERVATION',
                'limit': 2000
            },
            # Запрос 3: Менее строгий фильтр
            {
                'country': 'RU',
                'stateProvince': region_name_en,
                'kingdom': 'Animalia',
                'hasCoordinate': 'true',
                'limit': 2000
            }
        ]

        for i, params in enumerate(params_list):
            print(f"🔗 Попытка {i + 1}: class={params.get('class', 'Animalia')}")

            # Проверяем кэш для этих параметров
            cached_data = self.data_manager.get_api_cache(params)
            if cached_data:
                print("♻️ Используем кэшированные данные API")
                return cached_data

            try:
                response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    print(f"📊 API вернул {data['count']} записей")

                    if data['count'] > 0:
                        # Принудительная фильтрация на нашей стороне
                        animal_data = self._process_api_response_strict(data.get('results', []))

                        if animal_data:
                            # Сохраняем в кэш
                            self.data_manager.save_api_cache(params, animal_data)
                            print(f"💾 Сохранено в кэш: {len(animal_data)} животных")
                            return animal_data
                        else:
                            print("⚠️ Записи найдены, но не прошли строгую фильтрацию")
                            # Покажем что именно нашли
                            self._debug_first_records(data.get('results', [])[:3])
                    else:
                        print("❌ Записей не найдено")

                else:
                    print(f"❌ Ошибка API: {response.status_code}")

            except Exception as e:
                print(f"❌ Ошибка при запросе к API: {e}")

        return []

    def _process_api_response(self, records):
        """Обрабатывает ответ от API с прогресс-баром и оптимизацией"""
        animal_data = []
        rejected_records = []

        total_records = len(records)
        print(f"🔍 Анализируем {total_records} записей...")

        # Добавляем прогресс-бар
        for i, record in enumerate(tqdm(records, desc="Обработка записей", unit="rec")):
            # Показываем детали только для первых 3 записей
            if i < 3:
                print(f"\n📋 ЗАПИСЬ {i + 1}:")
                print(f"   Научное название: {record.get('scientificName', 'N/A')}")
                print(f"   Kingdom: {record.get('kingdom', 'N/A')}")
                print(f"   Phylum: {record.get('phylum', 'N/A')}")
                print(f"   Class: {record.get('class', 'N/A')}")

            # Оптимизированная проверка на животных
            kingdom = record.get('kingdom', '').lower()
            phylum = record.get('phylum', '').lower()
            class_name = record.get('class', '').lower()

            # Быстрая проверка - исключаем явные не-животные
            if kingdom in ['plantae', 'fungi']:
                rejected_records.append(('not_animal', record.get('scientificName')))
                continue

            # Проверяем признаки животных
            is_animal = (
                    kingdom == 'animalia' or
                    phylum in ['chordata', 'arthropoda', 'mollusca'] or
                    class_name in ['mammalia', 'aves', 'reptilia', 'amphibia', 'actinopterygii', 'insecta']
            )

            if not is_animal:
                rejected_records.append(('not_animal', record.get('scientificName')))
                continue

            # Если дошли сюда - это животное
            species_key = record.get('speciesKey')

            # Используем кэш для русских названий чтобы ускорить процесс
            common_name_ru = self._get_russian_common_name_cached(species_key)

            animal_info = {
                'scientific_name': record.get('scientificName', 'Не указано'),
                'common_name': common_name_ru,
                'kingdom': record.get('kingdom', 'Не указано'),
                'phylum': record.get('phylum', 'Не указано'),
                'class': record.get('class', 'Не указано'),
                'order': record.get('order', 'Не указано'),
                'family': record.get('family', 'Не указано'),
                'genus': record.get('genus', 'Не указано'),
                'species': record.get('species', 'Не указано'),
                'decimalLatitude': record.get('decimalLatitude'),
                'decimalLongitude': record.get('decimalLongitude'),
                'locality': record.get('locality', 'Не указано'),
                'stateProvince': record.get('stateProvince', 'Не указано'),
                'country': record.get('country', 'Не указано'),
                'eventDate': record.get('eventDate', 'Не указано'),
                'basisOfRecord': record.get('basisOfRecord', 'Не указано'),
                'speciesKey': species_key,
                'record_id': record.get('key')
            }
            animal_data.append(animal_info)

        # Статистика отсева
        print(f"\n📊 СТАТИСТИКА ФИЛЬТРАЦИИ:")
        print(f"✅ Принято животных: {len(animal_data)}")
        print(f"❌ Отклонено записей: {len(rejected_records)}")

        return animal_data

    def get_animals_by_coordinates_radius(self, latitude, longitude, radius_km=50, limit=1000):
        """Поиск животных в радиусе от координат"""
        print(f"📍 Поиск в радиусе {radius_km} км от {latitude}, {longitude}")

        base_url = "https://api.gbif.org/v1"

        params = {
            'decimalLatitude': latitude,
            'decimalLongitude': longitude,
            'coordinateUncertaintyInMeters': radius_km * 1000,
            'class': 'Mammalia,Aves,Reptilia,Amphibia,Insecta',
            'hasCoordinate': 'true',
            'basisOfRecord': 'HUMAN_OBSERVATION,OBSERVATION',
            'limit': limit
        }

        try:
            response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Найдено {data['count']} записей в радиусе {radius_km} км")

                animal_data = self._process_api_response_strict(data.get('results', []))
                return animal_data
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Ошибка при поиске по радиусу: {e}")
            return []

    def _debug_first_records(self, records):
        """Показывает детальную информацию о первых записях"""
        print("\n🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О НАЙДЕННЫХ ЗАПИСЯХ:")
        for i, record in enumerate(records):
            print(f"\n{i + 1}. {record.get('scientificName', 'N/A')}")
            print(f"   Kingdom: {record.get('kingdom', 'N/A')}")
            print(f"   Phylum: {record.get('phylum', 'N/A')}")
            print(f"   Class: {record.get('class', 'N/A')}")
            print(f"   Order: {record.get('order', 'N/A')}")
            print(f"   BasisOfRecord: {record.get('basisOfRecord', 'N/A')}")
            print(f"   Dataset: {record.get('datasetName', 'N/A')}")

    def search_known_russian_animals(self, region_name_en, limit=100):
        """Поиск конкретных известных животных России"""
        print(f"🔍 Поиск известных животных России в регионе {region_name_en}")

        # Известные животные России
        known_animals = [
            "Ursus arctos",  # Бурый медведь
            "Canis lupus",  # Волк
            "Vulpes vulpes",  # Лисица
            "Lepus timidus",  # Заяц-беляк
            "Sciurus vulgaris",  # Обыкновенная белка
            "Cervus elaphus",  # Благородный олень
            "Alces alces",  # Лось
            "Capreolus capreolus",  # Косуля
            "Lynx lynx",  # Рысь
            "Martes zibellina",  # Соболь
            "Mustela erminea",  # Горностай
            "Meles meles",  # Барсук
            "Castor fiber",  # Обыкновенный бобр
            "Sus scrofa",  # Кабан
            "Erinaceus europaeus",  # Обыкновенный ёж
            "Lacerta agilis",  # Прыткая ящерица
            "Natrix natrix",  # Обыкновенный уж
            "Bombina bombina",  # Краснобрюхая жерлянка
            "Rana temporaria"  # Травяная лягушка
        ]

        base_url = "https://api.gbif.org/v1"
        all_animals = []

        for animal in known_animals[:10]:  # Ограничим для скорости
            params = {
                'scientificName': animal,
                'country': 'RU',
                'stateProvince': region_name_en,
                'hasCoordinate': 'true',
                'limit': 10
            }

            try:
                response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data['count'] > 0:
                        print(f"✅ {animal}: {len(data['results'])} записей")
                        all_animals.extend(data['results'])
                    else:
                        print(f"❌ {animal}: не найдено")
                time.sleep(0.2)  # Пауза между запросами
            except Exception as e:
                print(f"❌ Ошибка при поиске {animal}: {e}")

        animal_data = self._process_api_response(all_animals)
        print(f"🎯 Найдено {len(animal_data)} животных известных видов")
        return animal_data

    def get_animals_by_region(self, region_name_ru, force_update=False):
        """Основной метод получения животных по региону"""
        # Получаем правильное название региона для GBIF
        region_name_en = self.get_correct_region_name(region_name_ru)
        print(f"🎯 Используем название региона для GBIF: {region_name_en}")

        # Нормализуем имя для файла
        normalized_name = "".join(c for c in region_name_en if c.isalnum()).lower()

        # Проверяем, есть ли данные в локальном хранилище
        if not force_update and self.data_manager.region_exists(normalized_name):
            print(f"📁 Используем локальные данные для {region_name_ru}")
            region_data = self.data_manager.get_region_data(normalized_name)
            if region_data:
                # Переводим данные с прогресс-баром
                print("🔤 Перевод таксономии на русский...")
                translated_data = []

                with tqdm(total=len(region_data), desc="🔤 Перевод данных", unit="animal",
                          bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as pbar:
                    for animal in region_data:
                        translated_data.append(self.translator.translate_animal_data(animal))
                        pbar.update(1)

                return translated_data

        # Получаем все данные через API с пагинацией
        print(f"🌐 Запрашиваем ВСЕ данные через API для {region_name_ru} ({region_name_en})")

        animal_data = self._fetch_from_api_large(region_name_en, region_name_ru)

        if animal_data:
            # Переводим данные перед сохранением
            print("🔤 Перевод таксономии на русский...")
            translated_data = []

            # Создаем прогресс-бар с известным общим количеством
            with tqdm(total=len(animal_data), desc="🔤 Перевод данных", unit="animal",
                      bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as pbar:
                for animal in animal_data:
                    translated_data.append(self.translator.translate_animal_data(animal))
                    pbar.update(1)

            # Сохраняем данные с нормализованным именем
            success = self.data_manager.save_region_data(region_name_en, region_name_ru, translated_data)
            if success:
                print(f"💾 Данные сохранены для региона {region_name_ru} (файл: {normalized_name}.json)")
            return translated_data
        else:
            print(f"❌ Не удалось получить данные для {region_name_ru}")
            return []

    def _fetch_from_api_large(self, region_name_en, region_name_ru, batch_size=300):
        """Получает все данные через GBIF API с пагинацией"""
        base_url = "https://api.gbif.org/v1"

        all_animal_data = []
        offset = 0
        total_processed = 0
        has_more_data = True
        max_retries = 3  # Максимальное количество попыток повтора

        print(f"🔗 Начинаем загрузку данных пачками по {batch_size} записей...")

        # Получаем приблизительное общее количество
        try:
            count_response = requests.get(f"{base_url}/occurrence/search",
                                          params={
                                              'country': 'RU',
                                              'stateProvince': region_name_en,
                                              'kingdom': 'Animalia',
                                              'limit': 0
                                          },
                                          timeout=30)
            if count_response.status_code == 200:
                total_estimate = count_response.json().get('count', 0)
                print(f"📊 Приблизительно всего записей: {total_estimate}")
            else:
                total_estimate = 0
                print(f"⚠️ Не удалось получить общее количество: {count_response.status_code}")
        except Exception as e:
            total_estimate = 0
            print(f"⚠️ Ошибка при получении общего количества: {e}")

        # Создаем прогресс-бар
        pbar = tqdm(total=total_estimate, desc="📥 Загрузка данных", unit="rec",
                    bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}')

        while has_more_data:
            # Параметры запроса с пагинацией
            params = {
                'country': 'RU',
                'stateProvince': region_name_en,
                'kingdom': 'Animalia',
                'limit': batch_size,
                'offset': offset
            }

            # Проверяем кэш для текущей пачки
            cached_batch = self.data_manager.get_api_cache(params)
            if cached_batch:
                print(f"♻️ Используем кэшированную пачку {offset // batch_size + 1}")
                all_animal_data.extend(cached_batch)
                pbar.update(len(cached_batch))
                offset += batch_size
                continue

            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    print(f"\n📥 Загружаем пачку {offset // batch_size + 1}...")
                    response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        batch_records = data.get('results', [])

                        if not batch_records:
                            print("✅ Все данные загружены")
                            has_more_data = False
                            break

                        # Обрабатываем текущую пачку
                        animal_data_batch = self._process_api_response_batch(batch_records)
                        all_animal_data.extend(animal_data_batch)

                        total_processed += len(batch_records)
                        pbar.update(len(batch_records))
                        pbar.set_postfix({'животных': len(all_animal_data)})

                        print(f"\n✅ Пачка {offset // batch_size + 1}: {len(animal_data_batch)} животных")

                        # Сохраняем пачку в кэш
                        self.data_manager.save_api_cache(params, animal_data_batch)

                        # Проверяем, есть ли еще данные
                        if len(batch_records) < batch_size:
                            print("✅ Достигнут конец данных")
                            has_more_data = False
                        else:
                            offset += batch_size

                        success = True

                    elif response.status_code == 503:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = retry_count * 10  # Увеличиваем время ожидания
                            print(
                                f"⏸️ Сервер перегружен (503). Попытка {retry_count}/{max_retries} через {wait_time} сек...")
                            time.sleep(wait_time)
                        else:
                            print("❌ Сервер постоянно возвращает ошибку 503. Прерываем загрузку.")
                            has_more_data = False
                            break

                    else:
                        print(f"❌ Ошибка API: {response.status_code}")
                        has_more_data = False
                        break

                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"⏰ Таймаут. Попытка {retry_count}/{max_retries}...")
                        time.sleep(5)
                    else:
                        print("❌ Превышено количество попыток при таймауте")
                        has_more_data = False
                        break

                except Exception as e:
                    print(f"❌ Неожиданная ошибка при загрузке пачки {offset // batch_size + 1}: {e}")
                    has_more_data = False
                    break

            # Небольшая пауза между запросами даже при успехе
            if success:
                time.sleep(0.5)

        pbar.close()
        print(f"\n🎯 ИТОГО: обработано {total_processed} записей, найдено {len(all_animal_data)} животных")

        return all_animal_data

    def _process_api_response_batch(self, records):
        """Быстрая обработка пачки записей с улучшенной фильтрацией"""
        animal_data = []

        for record in records:
            # Быстрая проверка на животных
            kingdom = record.get('kingdom', '').lower()
            phylum = record.get('phylum', '').lower()
            class_name = record.get('class', '').lower()

            # Исключаем явные не-животные и неинтересные группы
            if kingdom in ['plantae', 'fungi']:
                continue

            # Исключаем червей, насекомых и другие неинтересные группы
            if any(unwanted in phylum.lower() for unwanted in ['annelida', 'nematoda', 'platyhelminthes']):
                continue

            if any(unwanted in class_name.lower() for unwanted in ['clitellata', 'insecta', 'arachnida', 'gastropoda']):
                continue

            # Проверяем признаки интересных животных
            is_interesting_animal = (
                    kingdom == 'animalia' and (
                    phylum in ['chordata'] or  # Только хордовые
                    class_name in ['mammalia', 'aves', 'reptilia', 'amphibia', 'actinopterygii']
            # Только основные классы
            )
            )

            if not is_interesting_animal:
                continue

            # Создаем запись животного
            species_key = record.get('speciesKey')
            common_name_ru = self._get_russian_common_name_cached(species_key)

            animal_info = {
                'scientific_name': record.get('scientificName', 'Не указано'),
                'common_name': common_name_ru,
                'kingdom': record.get('kingdom', 'Не указано'),
                'phylum': record.get('phylum', 'Не указано'),
                'class': record.get('class', 'Не указано'),
                'order': record.get('order', 'Не указано'),
                'family': record.get('family', 'Не указано'),
                'genus': record.get('genus', 'Не указано'),
                'species': record.get('species', 'Не указано'),
                'decimalLatitude': record.get('decimalLatitude'),
                'decimalLongitude': record.get('decimalLongitude'),
                'locality': record.get('locality', 'Не указано'),
                'stateProvince': record.get('stateProvince', 'Не указано'),
                'country': record.get('country', 'Не указано'),
                'eventDate': record.get('eventDate', 'Не указано'),
                'basisOfRecord': record.get('basisOfRecord', 'Не указано'),
                'speciesKey': species_key,
                'record_id': record.get('key')
            }
            animal_data.append(animal_info)

        return animal_data

    def get_total_records_count(self, region_name_en):
        """Получает общее количество записей для региона"""
        base_url = "https://api.gbif.org/v1"

        params = {
            'country': 'RU',
            'stateProvince': region_name_en,
            'kingdom': 'Animalia',
            'limit': 0
        }

        try:
            response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get('count', 0)
        except Exception as e:
            print(f"⚠️ Не удалось получить общее количество записей: {e}")

        return 0

    def _fetch_from_api(self, region_name_en, region_name_ru):
        """Получает данные через GBIF API"""
        base_url = "https://api.gbif.org/v1"

        # Параметры запроса
        params = {
            'country': 'RU',
            'stateProvince': region_name_en,
            'kingdom': 'Animalia',
            'limit': 2000
        }

        # Проверяем кэш
        cached_data = self.data_manager.get_api_cache(params)
        if cached_data:
            print("♻️ Используем кэшированные данные API")
            return cached_data

        try:
            print(f"🔗 Отправляем запрос к GBIF API...")
            response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"📊 API вернул {data['count']} записей")

                animal_data = self._process_api_response(data.get('results', []))

                # Сохраняем в кэш
                self.data_manager.save_api_cache(params, animal_data)
                print(f"💾 Сохранено в кэш: {len(animal_data)} животных")

                return animal_data
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Ошибка при запросе к API: {e}")
            return []

    def get_correct_region_name(self, region_name_ru):
        """Определяет правильное название региона для GBIF API"""
        region_mapping = {
            'Забайкальский край': 'Zabaykalsky Krai',
            'Забайкальский': 'Zabaykalsky Krai',
            'Zabaykalsky': 'Zabaykalsky Krai',
            'Крым': 'Crimea',
            'Республика Крым': 'Crimea',
            'Москва': 'Moscow',
            'Московская': 'Moscow',
            'Санкт-Петербург': 'Saint Petersburg',
            'Ленинградская': 'Leningrad',
            'Краснодарский край': 'Krasnodar Krai',
            'Краснодарская': 'Krasnodar Krai',
            'Новосибирская': 'Novosibirsk',
            'Амурская': 'Amur',
            'Брянская': 'Bryansk',
            'Нижегородская': 'Nizhny Novgorod',
            'Татарстан': 'Tatarstan',
            'Сахалин': 'Sakhalin'
        }

        return region_mapping.get(region_name_ru, region_name_ru)

    def _process_api_response(self, records):
        """Обрабатывает ответ от API - с детальной отладкой"""
        animal_data = []
        rejected_records = []

        print(f"🔍 Анализируем {len(records)} записей...")

        for i, record in enumerate(records):
            # Детальная информация о первых 3 записях для отладки
            if i < 3:
                print(f"\n📋 ЗАПИСЬ {i + 1}:")
                print(f"   Научное название: {record.get('scientificName', 'N/A')}")
                print(f"   Kingdom: {record.get('kingdom', 'N/A')}")
                print(f"   Phylum: {record.get('phylum', 'N/A')}")
                print(f"   Class: {record.get('class', 'N/A')}")
                print(f"   BasisOfRecord: {record.get('basisOfRecord', 'N/A')}")

            # Гибкая проверка на животных
            kingdom = record.get('kingdom', '').lower()
            phylum = record.get('phylum', '').lower()
            class_name = record.get('class', '').lower()
            basis_of_record = record.get('basisOfRecord', '').lower()

            # Признаки животных
            animal_indicators = [
                kingdom == 'animalia',
                phylum in ['chordata', 'arthropoda', 'mollusca', 'annelida', 'cnidaria', 'echinodermata'],
                class_name in [
                    'mammalia', 'aves', 'reptilia', 'amphibia', 'actinopterygii',
                    'insecta', 'arachnida', 'gastropoda', 'bivalvia', 'malacostraca',
                    'actinopoda', 'aves', 'branchiopoda', 'cephalopoda', 'clitellata',
                    'demospongiae', 'entognatha', 'eurotatoria', 'gymnolaemata',
                    'holothuroidea', 'hydrozoa', 'maxillopoda', 'merostomata',
                    'monogononta', 'oligochaeta', 'ostracoda', 'polychaeta',
                    'polyplacophora', 'scyphozoa', 'tentaculata', 'turbellaria'
                ]
            ]

            # Признаки растений (исключаем)
            plant_indicators = [
                kingdom == 'plantae',
                phylum in ['magnoliophyta', 'tracheophyta', 'bryophyta', 'marchantiophyta'],
                class_name in ['magnoliopsida', 'liliopsida', 'pinopsida', 'lycopodiopsida'],
                'plant' in basis_of_record,
                'herbarium' in basis_of_record
            ]

            # Признаки грибов (исключаем)
            fungus_indicators = [
                kingdom == 'fungi',
                phylum in ['ascomycota', 'basidiomycota']
            ]

            is_animal = any(animal_indicators)
            is_plant = any(plant_indicators)
            is_fungus = any(fungus_indicators)

            if is_plant or is_fungus:
                if i < 3:
                    print(f"   ❌ ОТКЛОНЕНО: растение или гриб")
                rejected_records.append(('plant/fungus', record.get('scientificName')))
                continue

            if not is_animal:
                if i < 3:
                    print(f"   ❌ ОТКЛОНЕНО: не животное")
                rejected_records.append(('not_animal', record.get('scientificName')))
                continue

            # Если дошли сюда - это животное
            if i < 3:
                print(f"   ✅ ПРИНЯТО: животное")

            species_key = record.get('speciesKey')
            common_name_ru = self._get_russian_common_name(species_key)

            animal_info = {
                'scientific_name': record.get('scientificName', 'Не указано'),
                'common_name': common_name_ru,
                'kingdom': record.get('kingdom', 'Не указано'),
                'phylum': record.get('phylum', 'Не указано'),
                'class': record.get('class', 'Не указано'),
                'order': record.get('order', 'Не указано'),
                'family': record.get('family', 'Не указано'),
                'genus': record.get('genus', 'Не указано'),
                'species': record.get('species', 'Не указано'),
                'decimalLatitude': record.get('decimalLatitude'),
                'decimalLongitude': record.get('decimalLongitude'),
                'locality': record.get('locality', 'Не указано'),
                'stateProvince': record.get('stateProvince', 'Не указано'),
                'country': record.get('country', 'Не указано'),
                'eventDate': record.get('eventDate', 'Не указано'),
                'basisOfRecord': record.get('basisOfRecord', 'Не указано'),
                'speciesKey': species_key,
                'record_id': record.get('key')
            }
            animal_data.append(animal_info)

        # Статистика отсева
        print(f"\n📊 СТАТИСТИКА ФИЛЬТРАЦИИ:")
        print(f"✅ Принято животных: {len(animal_data)}")
        print(f"❌ Отклонено записей: {len(rejected_records)}")

        if rejected_records:
            rejection_reasons = {}
            for reason, name in rejected_records:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            print(f"📈 Причины отклонения: {rejection_reasons}")

        return animal_data

    def get_animals_by_coordinates(self, latitude, longitude, force_update=False):
        """Получает животных по координатам - пробуем оба метода"""
        print(f"📍 Поиск животных для координат: {latitude}, {longitude}")

        # Сначала пробуем через определение региона
        region_ru, region_en = self.get_region_by_coordinates(latitude, longitude)
        print(f"🎯 Определен регион: {region_ru} -> {region_en}")

        # Получаем правильное название для GBIF
        correct_region_en = self.get_correct_region_name(region_ru)
        print(f"🎯 Используем название для GBIF: {correct_region_en}")

        animals_by_region = self.get_animals_by_region(region_ru, force_update)

        if animals_by_region:
            print(f"✅ Найдено {len(animals_by_region)} животных через регион '{region_ru}'")
            return animals_by_region
        else:
            print(f"❌ Через регион '{region_ru}' не найдено животных, пробуем прямой поиск...")
            # Пробуем прямой поиск по координатам
            animals_direct = self.get_animals_by_coordinates_direct(latitude, longitude)

            if animals_direct:
                print(f"✅ Прямой поиск нашел {len(animals_direct)} животных")
                # Сохраняем найденных животных под регионом
                if region_ru != "Неизвестный регион":
                    self.data_manager.save_region_data(correct_region_en, region_ru, animals_direct)
                return animals_direct
            else:
                print("❌ Оба метода не дали результатов")
                return []

    def get_animals_by_coordinates_direct(self, latitude, longitude, radius_km=100, limit=1000):
        """Прямой поиск животных по координатам без определения региона"""
        print(f"📍 Прямой поиск по координатам: {latitude}, {longitude}")

        base_url = "https://api.gbif.org/v1"

        params = {
            'decimalLatitude': latitude,
            'decimalLongitude': longitude,
            'coordinateUncertaintyInMeters': radius_km * 1000,
            'kingdom': 'Animalia',
            'hasCoordinate': 'true',
            'limit': limit
        }

        try:
            response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Прямой поиск вернул {data['count']} записей")

                animal_data = self._process_api_response(data.get('results', []))
                return animal_data
            else:
                print(f"❌ Ошибка прямого поиска: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Ошибка при прямом поиске: {e}")
            return []

    def _get_russian_common_name(self, species_key):
        """Получает русское название вида"""
        if not species_key:
            return 'Не указано'

        try:
            response = requests.get(f"https://api.gbif.org/v1/species/{species_key}/vernacularNames", timeout=5)
            if response.status_code == 200:
                vernacular_data = response.json()
                for vernacular in vernacular_data.get('results', []):
                    if vernacular.get('language') == 'rus':
                        return vernacular.get('vernacularName')
        except:
            pass

        return 'Не указано'

    def test_popular_regions(self):
        """Тестирует поиск в популярных регионах"""
        test_coordinates = [
            (55.7558, 37.6173, "Москва"),  # Москва
            (59.9343, 30.3351, "Санкт-Петербург"),  # СПб
            (45.0355, 38.9753, "Краснодар"),  # Краснодар
            (56.8389, 60.6057, "Екатеринбург"),  # Свердловская
            (54.9833, 73.3667, "Омск"),  # Омская
            (56.3269, 44.0065, "Нижний Новгород"),  # Нижегородская
            (55.7963, 49.1088, "Казань"),  # Татарстан
        ]

        print("\n🧪 ТЕСТИРОВАНИЕ ПОПУЛЯРНЫХ РЕГИОНОВ:")
        print("=" * 50)

        for lat, lon, region_name in test_coordinates:
            print(f"\n📍 Тестируем {region_name} ({lat}, {lon})")
            animals = self.get_animals_by_coordinates(lat, lon)

            if animals:
                print(f"✅ УСПЕХ: найдено {len(animals)} животных")
                # Покажем топ-3
                df = pd.DataFrame(animals)
                top_species = df['scientific_name'].value_counts().head(3)
                for species, count in top_species.items():
                    common_name = df[df['scientific_name'] == species]['common_name'].iloc[0]
                    print(
                        f"   • {species} ({common_name if common_name != 'Не указано' else 'нет названия'}) - {count}")
            else:
                print(f"❌ НЕ УДАЛОСЬ: животных не найдено")

    def analyze_region(self, region_name_ru):
        """Анализирует данные региона"""
        animals = self.get_animals_by_region(region_name_ru)

        if not animals:
            print(f"❌ Нет данных для региона {region_name_ru}")
            return

        print(f"\n{'=' * 60}")
        print(f"🐾 АНАЛИЗ ЖИВОТНЫХ В {region_name_ru.upper()} ОБЛАСТИ")
        print(f"{'='*60}")

        print(f"\n📊 СТАТИСТИКА:")
        print(f"Всего записей: {len(animals)}")
        print(f"Уникальных видов: {len(set([a['scientific_name'] for a in animals]))}")

        # Распределение по классам
        class_counts = {}
        for animal in animals:
            class_name = animal.get('class_ru', animal.get('class', 'Не указано'))
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО КЛАССАМ:")
        for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(animals)) * 100
            print(f"  {class_name}: {count} ({percentage:.1f}%)")

        # Топ видов
        species_counts = {}
        for animal in animals:
            species_name = animal['scientific_name']
            common_name = animal.get('common_name', 'Нет русского названия')
            species_counts[species_name] = species_counts.get(species_name, {'count': 0, 'common_name': common_name})
            species_counts[species_name]['count'] += 1

        top_species = sorted(species_counts.items(), key=lambda x: x[1]['count'], reverse=True)[:5]

        if top_species:
            print(f"\n🏆 ТОП-5 ВИДОВ:")
            for i, (species, info) in enumerate(top_species, 1):
                common_name = info['common_name']
                class_name = next(a.get('class_ru', a.get('class', 'Не указано')) for a in animals if
                                   a['scientific_name'] == species)
                print(f"{i}. {species}")
                print(f"   📝 {common_name}" if common_name != 'Не указано' else "   📝 Нет русского названия")
                print(f"   🐾 {class_name}")
                print(f"   🎯 Находок: {info['count']}")
                print()

    def show_detailed_animal_info(self, animals, count=5):
        """Показывает детальную информацию о животных"""
        print(f"\n🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О {count} ЖИВОТНЫХ:")
        for i, animal in enumerate(animals[:count], 1):
            print(f"\n{i}. {animal.get('common_name', 'Нет названия')}")
            print(f"   Научное название: {animal['scientific_name']}")
            print(f"   Тип: {animal.get('phylum_ru', animal.get('phylum', 'Не указано'))}")
            print(f"   Класс: {animal.get('class_ru', animal.get('class', 'Не указано'))}")
            print(f"   Отряд: {animal.get('order_ru', animal.get('order', 'Не указано'))}")
            print(f"   Семейство: {animal.get('family_ru', animal.get('family', 'Не указано'))}")
            print(f"   Род: {animal.get('genus_ru', animal.get('genus', 'Не указано'))}")
            if animal.get('locality') and animal['locality'] != 'Не указано':
                print(f"   Место: {animal['locality']}")
            if animal.get('eventDate') and animal['eventDate'] != 'Не указано':
                print(f"   Дата наблюдения: {animal['eventDate']}")

    def get_animals_combined(self, region_name_ru, force_update=False):
        """Комбинированный поиск животных: GBIF + локальная база с фильтрацией"""
        print(f"🎯 КОМБИНИРОВАННЫЙ ПОИСК ДЛЯ {region_name_ru}")

        # 1. Пробуем получить данные из GBIF
        gbif_animals = self.get_animals_by_region(region_name_ru, force_update)

        # 2. Получаем животных из локальной базы данных
        local_animals = self.animals_db.get_animals_by_region(region_name_ru)
        print(f"📚 Локальная база: {len(local_animals)} животных")

        # 3. Объединяем и убираем дубликаты
        all_animals = self._merge_animal_data(gbif_animals, local_animals)

        # 4. ПРИМЕНЯЕМ ФИЛЬТРАЦИЮ К ОБЪЕДИНЕННЫМ ДАННЫМ
        filtered_animals = self.filter_animals_data(all_animals, min_count=1)

        print(f"🎉 ИТОГО: {len(filtered_animals)} животных ({len(gbif_animals)} из GBIF + {len(local_animals)} из базы)")
        return filtered_animals

    def _merge_animal_data(self, gbif_animals, local_animals):
        """Объединяет данные из GBIF и локальной базы"""
        merged_animals = []
        seen_species = set()

        # Сначала добавляем животных из GBIF
        for animal in gbif_animals:
            species = animal.get('scientific_name')
            if species and species not in seen_species:
                merged_animals.append(animal)
                seen_species.add(species)

        # Затем добавляем животных из локальной базы (только тех, кого нет в GBIF)
        for animal in local_animals:
            species = animal.get('scientific_name')
            if species and species not in seen_species:
                # Добавляем недостающие поля для животных из базы данных
                enhanced_animal = {
                    'scientific_name': animal['scientific_name'],
                    'common_name': animal['common_name'],
                    'class_ru': animal.get('class_ru', 'Не указано'),
                    'phylum_ru': animal.get('phylum_ru', 'Хордовые'),
                    'order_ru': 'Не указано',
                    'family_ru': 'Не указано',
                    'genus_ru': 'Не указано',
                    'source': 'local_db',
                    'region': animal.get('region', 'Не указано')
                }
                merged_animals.append(enhanced_animal)
                seen_species.add(species)

        return merged_animals

    def analyze_region_combined(self, region_name_ru):
        """Улучшенный анализ с комбинированными данными и фильтрацией"""
        animals = self.get_animals_combined(region_name_ru)

        if not animals:
            print(f"❌ Нет данных для региона {region_name_ru}")
            return

        # ФИЛЬТРУЕМ ДАННЫЕ - убираем редкие и неинформативные записи
        filtered_animals = self.filter_animals_data(animals, min_count=2)

        # Разделяем животных по источникам (после фильтрации)
        gbif_animals = [a for a in filtered_animals if a.get('source') != 'local_db']
        local_animals = [a for a in filtered_animals if a.get('source') == 'local_db']

        print(f"\n{'=' * 60}")
        print(f"🐾 КОМБИНИРОВАННЫЙ АНАЛИЗ ЖИВОТНЫХ В {region_name_ru.upper()}")
        print(f"{'=' * 60}")

        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"Всего животных: {len(filtered_animals)}")
        print(f"• Найдено в GBIF: {len(gbif_animals)}")
        print(f"• Из базы данных: {len(local_animals)}")

        if not filtered_animals:
            print("🎯 После фильтрации не осталось значимых данных")
            return

        # Анализ по классам (только для отфильтрованных данных)
        class_stats = {}
        for animal in filtered_animals:
            class_name = animal.get('class_ru', 'Не указано')
            class_stats[class_name] = class_stats.get(class_name, 0) + 1

        print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО КЛАССАМ:")
        for class_name, count in sorted(class_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(filtered_animals)) * 100
            print(f"  {class_name}: {count} ({percentage:.1f}%)")

        # Показываем примеры животных из разных источников
        if gbif_animals:
            print(f"\n🔍 ПРИМЕРЫ ИЗ GBIF:")
            for animal in gbif_animals[:5]:
                name = animal.get('common_name', animal['scientific_name'])
                print(f"  • {name}")

        if local_animals:
            print(f"\n📚 ПОПУЛЯРНЫЕ ВИДЫ ИЗ БАЗЫ ДАННЫХ:")
            for animal in local_animals[:8]:
                print(f"  • {animal['common_name']} ({animal['scientific_name']})")

    def filter_animals_data(self, animals, min_count=2, exclude_classes=None):
        """Фильтрует данные о животных - убираем червей, пауков и неинтересные классы"""
        if exclude_classes is None:
            # Расширенный список исключаемых классов
            exclude_classes = [
                'Clitellata', 'Кольчатые черви', 'Олигохеты',  # Черви
                'Паукообразные', 'Arachnida',  # Пауки
                'Насекомые', 'Insecta',  # Насекомые
                'Диплоподы', 'Многоножки',  # Многоножки
                'Губки', 'Porifera',  # Губки
                'Брюхоногие', 'Gastropoda',  # Улитки
                'Двустворчатые', 'Bivalvia',  # Моллюски
                'Коллемболы', 'Collembola',  # Ногохвостки
                'Ракообразные', 'Crustacea',  # Раки
                'Нематоды', 'Nematoda',  # Круглые черви
                'Плоские черви', 'Platyhelminthes',  # Плоские черви
                'Коловратки', 'Rotifera',  # Коловратки
                'Тихоходки', 'Tardigrada',  # Тихоходки
                'Мшанки', 'Bryozoa'  # Мшанки
            ]

        # Сначала группируем по видам и считаем количество
        species_counts = {}
        for animal in animals:
            species = animal.get('scientific_name')
            if species and species != 'Не указано':
                species_counts[species] = species_counts.get(species, 0) + 1

        # Фильтруем животных
        filtered_animals = []
        for animal in animals:
            species = animal.get('scientific_name')
            animal_class = animal.get('class_ru', animal.get('class', 'Не указано'))

            # Проверяем критерии исключения
            should_include = (
                    species and
                    species != 'Не указано' and
                    species_counts.get(species, 0) >= min_count and
                    animal_class not in exclude_classes and
                    not self._is_uninformative_animal(animal) and
                    not self._is_worm_or_insect(animal)  # Дополнительная проверка
            )

            if should_include:
                filtered_animals.append(animal)

        removed_count = len(animals) - len(filtered_animals)
        if removed_count > 0:
            print(f"🔍 Фильтрация: убрано {removed_count} незначимых записей (черви, пауки, насекомые и др.)")

        return filtered_animals

    def _is_worm_or_insect(self, animal):
        """Дополнительная проверка на червей, насекомых и другие неинтересные группы"""
        scientific_name = animal.get('scientific_name', '').lower()
        common_name = animal.get('common_name', '').lower()
        phylum = animal.get('phylum', '').lower()
        animal_class = animal.get('class', '').lower()

        # Признаки червей
        worm_indicators = [
            'clitellata', 'oligochaeta', 'enchytraeidae', 'annelida',
            'nematoda', 'platyhelminthes', 'rotifera', 'tardigrada',
            'червь', 'worm', 'нематод', 'коловратк'
        ]

        # Признаки насекомых и пауков
        insect_indicators = [
            'insecta', 'arachnida', 'diplopoda', 'crustacea',
            'gastropoda', 'bivalvia', 'collembola', 'bryozoa',
            'насеком', 'паук', 'моллюск', 'ракообразн'
        ]

        # Проверяем по разным полям
        for field in [scientific_name, common_name, phylum, animal_class]:
            if any(indicator in field for indicator in worm_indicators + insect_indicators):
                return True

        return False

    def _is_uninformative_animal(self, animal):
        """Проверяет, является ли животное неинформативным"""
        scientific_name = animal.get('scientific_name', '').lower()
        common_name = animal.get('common_name', '').lower()

        # Признаки неинформативных записей
        uninformative_indicators = [
            # Слишком общие таксоны
            'idae', 'inae', 'iformes', 'acea', 'oidea',
            # Неопределенные названия
            'sp.', 'spp.', 'unknown', 'unidentified', 'indet.',
            # Лабораторные/домашние виды
            'mus musculus', 'rattus norvegicus', 'drosophila',
            # Ископаемые виды (часто имеют странные названия)
            'ites', 'ensis', 'oides'
        ]

        # Проверяем классы, которые всегда исключаем
        animal_class = animal.get('class_ru', '').lower()
        if any(unwanted in animal_class for unwanted in ['насекомые', 'паукообразные', 'черви', 'моллюски']):
            return True

        return any(indicator in scientific_name for indicator in uninformative_indicators)

# Основная программа
def main():
    finder = AnimalFinder()

    print("🐾 СИСТЕМА ПОИСКА ЖИВОТНЫХ ПО КООРДИНАТАМ")
    print("=" * 50)

    # Показываем статистику сохраненных регионов
    finder.show_regions_statistics()

    # Получаем доступные регионы
    available_regions = finder.get_available_regions_list()

    while True:
        print(f"\n🎯 ДОСТУПНЫЕ РЕГИОНЫ: {', '.join(available_regions)}")
        print("\nВыберите режим:")
        print("1. Поиск по координатам")
        print("2. Поиск по названию региона")
        print("3. Обновить статистику регионов")
        print("4. Выход")

        choice = input("\nВаш выбор (1-4): ").strip()

        if choice == '1':
            # Режим поиска по координатам
            try:
                lat_input = input("Введите широту (например, 55.7558): ").strip().replace(',', '.')
                lon_input = input("Введите долготу (например, 37.6173): ").strip().replace(',', '.')

                lat = float(lat_input)
                lon = float(lon_input)

                animals = finder.get_animals_by_coordinates(lat, lon)
                if animals:
                    region_ru, region_en = finder.get_region_by_coordinates(lat, lon)
                    finder.analyze_region_combined(region_ru)
                    finder.show_detailed_animal_info_improved(animals)
                else:
                    print("❌ Не удалось найти животных для данных координат")

            except ValueError:
                print("❌ Ошибка: введите корректные числовые значения координат")

        elif choice == '2':
            # Режим поиска по региону
            print(f"\n💡 Доступные регионы: {', '.join(available_regions)}")
            region_input = input("Введите название региона: ").strip()

            animals = finder.get_animals_by_region(region_input)
            if animals:
                finder.analyze_region_improved(region_input)
                finder.show_detailed_animal_info_improved(animals)
            else:
                print(f"❌ Не удалось найти животных для региона {region_input}")

        elif choice == '3':
            # Обновить статистику
            finder.show_regions_statistics()
            available_regions = finder.get_available_regions_list()

        elif choice == '4':
            print("👋 До свидания!")
            break

        else:
            print("❌ Неверный выбор, попробуйте снова")


if __name__ == "__main__":
    main()