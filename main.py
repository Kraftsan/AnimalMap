import requests
import pandas as pd
from utils.data_manager import DataManager
from utils.taxonomy_translator import TaxonomyTranslator
import time


class AnimalFinder:
    def __init__(self):
        self.data_manager = DataManager()
        self.translator = TaxonomyTranslator()
        self.region_translations = {
            'Амурская': 'Amur',
            'Московская': 'Moscow',
            'Ленинградская': 'Leningrad',
            'Краснодарская': 'Krasnodar',
            'Новосибирская': 'Novosibirsk'
        }

    def get_region_by_coordinates(self, latitude, longitude):
        """Определяет регион по координатам"""
        print(f"📍 Определяем регион для координат: {latitude}, {longitude}")
        region_ru, region_en = self.data_manager.get_region_by_coordinates(latitude, longitude)
        print(f"🎯 Найден регион: {region_ru} ({region_en})")
        return region_ru, region_en

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
        """Получает данные через GBIF API - улучшенные параметры"""
        base_url = "https://api.gbif.org/v1"

        # Улучшенные параметры запроса для животных
        params_list = [
            # Основной запрос - строгий фильтр животных
            {
                'country': 'RU',
                'stateProvince': region_name_en,
                'kingdom': 'Animalia',
                'hasCoordinate': 'true',  # Только записи с координатами
                'basisOfRecord': 'HUMAN_OBSERVATION,OBSERVATION',  # Только наблюдения
                'limit': 200
            },
            # Альтернативный запрос - менее строгий
            {
                'country': 'RU',
                'stateProvince': region_name_en,
                'kingdom': 'Animalia',
                'hasCoordinate': 'true',
                'limit': 200
            },
            # Запрос по основным классам животных
            {
                'country': 'RU',
                'stateProvince': region_name_en,
                'class': 'Mammalia,Aves,Reptilia,Amphibia,Insecta',
                'hasCoordinate': 'true',
                'limit': 200
            }
        ]

        for i, params in enumerate(params_list):
            print(f"🔗 Попытка {i + 1}: {params}")

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
                        animal_data = self._process_api_response(data.get('results', []))

                        if animal_data:
                            # Сохраняем в кэш
                            self.data_manager.save_api_cache(params, animal_data)
                            print(f"💾 Сохранено в кэш: {len(animal_data)} животных")
                            return animal_data
                        else:
                            print("⚠️ Записи найдены, но не прошли фильтрацию как животные")
                            # Покажем что именно нашли
                            self._debug_first_records(data.get('results', [])[:3])
                    else:
                        print("❌ Записей не найдено")

                else:
                    print(f"❌ Ошибка API: {response.status_code}")

            except Exception as e:
                print(f"❌ Ошибка при запросе к API: {e}")

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

    def search_known_russian_animals(self, region_name_en, limit=50):
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
        region_name_en = self.region_translations.get(region_name_ru, region_name_ru)

        # Проверяем, есть ли данные в локальном хранилище
        if not force_update and self.data_manager.region_exists(region_name_en):
            print(f"📁 Используем локальные данные для {region_name_ru}")
            region_data = self.data_manager.get_region_data(region_name_en)
            if region_data:
                # Переводим данные
                translated_data = [self.translator.translate_animal_data(animal) for animal in region_data]
                return translated_data

        # Получаем данные через API
        print(f"🌐 Запрашиваем данные через API для {region_name_ru}")

        # Сначала обычный поиск
        animal_data = self._fetch_from_api(region_name_en, region_name_ru)

        # Если не нашли, пробуем поиск известных животных
        if not animal_data:
            print(f"🦌 Пробуем поиск известных животных...")
            animal_data = self.search_known_russian_animals(region_name_en)

        if animal_data:
            # Переводим данные перед сохранением
            translated_data = [self.translator.translate_animal_data(animal) for animal in animal_data]

            # Сохраняем данные
            success = self.data_manager.save_region_data(region_name_en, region_name_ru, translated_data)
            if success:
                print(f"💾 Данные сохранены для региона {region_name_ru}")
            return translated_data
        else:
            print(f"❌ Не удалось получить данные для {region_name_ru}")
            return []

    def _fetch_from_api(self, region_name_en, region_name_ru):
        """Получает данные через GBIF API"""
        base_url = "https://api.gbif.org/v1"

        # Параметры запроса
        params = {
            'country': 'RU',
            'stateProvince': region_name_en,
            'kingdom': 'Animalia',
            'limit': 300
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

    def get_animals_by_coordinates_direct(self, latitude, longitude, radius_km=50, limit=200):
        """Прямой поиск животных по координатам без определения региона"""
        print(f"📍 Прямой поиск по координатам: {latitude}, {longitude}")

        base_url = "https://api.gbif.org/v1"

        params = {
            'decimalLatitude': latitude,
            'decimalLongitude': longitude,
            'coordinateUncertaintyInMeters': radius_km * 1000,
            'kingdom': 'Animalia',
            'limit': limit,
            'hasCoordinate': 'true'
        }

        try:
            print(f"🔗 Прямой запрос к API по координатам...")
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


# Основная программа
def main():
    finder = AnimalFinder()

    print("🐾 СИСТЕМА ПОИСКА ЖИВОТНЫХ ПО КООРДИНАТАМ")
    print("=" * 50)

    # Сначала покажем доступные регионы
    print("\n📊 Проверяем регионы с данными о животных...")
    available_regions = finder.check_available_regions()

    while True:
        print("\nВыберите режим:")
        print("1. Поиск по координатам")
        print("2. Поиск по названию региона")
        print("3. Обновить список регионов")
        print("4. Выход")

        choice = input("\nВаш выбор (1-4): ").strip()

        if choice == '1':
            # Режим поиска по координатам
            try:
                lat_input = input("Введите широту (например, 53.0): ").strip().replace(',', '.')
                lon_input = input("Введите долготу (например, 127.0): ").strip().replace(',', '.')

                lat = float(lat_input)
                lon = float(lon_input)

                animals = finder.get_animals_by_coordinates(lat, lon)
                if animals:
                    region_ru, region_en = finder.get_region_by_coordinates(lat, lon)
                    finder.analyze_region(region_ru)
                    finder.show_detailed_animal_info(animals)
                else:
                    print("❌ Не удалось найти животных для данных координат")
                    print("💡 Попробуйте координаты из регионов с данными (см. список выше)")

            except ValueError:
                print("❌ Ошибка: введите корректные числовые значения координат")

        elif choice == '2':
            # Режим поиска по региону
            print("\n💡 Рекомендуемые регионы:",
                  [r[0] for r in available_regions if r[3] > 0][:5] if available_regions else "Krasnodar, Amur")

            region_input = input("Введите название региона: ").strip()
            animals = finder.get_animals_by_region(region_input)
            if animals:
                finder.analyze_region(region_input)
                finder.show_detailed_animal_info(animals)
            else:
                print(f"❌ Не удалось найти животных для региона {region_input}")
                print("💡 Попробуйте английское название региона")

        elif choice == '3':
            # Обновить список регионов
            available_regions = finder.check_available_regions()

        elif choice == '4':
            print("👋 До свидания!")
            break

        else:
            print("❌ Неверный выбор, попробуйте снова")


if __name__ == "__main__":
    main()