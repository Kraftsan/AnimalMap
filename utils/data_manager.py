import json
import os
import hashlib
from datetime import datetime, timedelta
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class DataManager:
    def __init__(self, base_path="data"):
        self.base_path = base_path
        self.regions_path = os.path.join(base_path, "regions")
        self.cache_path = os.path.join(base_path, "cache", "api_cache.json")
        self.keys_path = os.path.join("config", "regions_keys.json")
        self.coordinates_path = os.path.join("config", "coordinates_regions.json")

        # Создаем директории если их нет
        os.makedirs(self.regions_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.keys_path), exist_ok=True)

        # Инициализируем файлы если их нет
        self._init_files()

        # Инициализируем геокодер
        self.geolocator = Nominatim(user_agent="animal_map_app")

    def _init_files(self):
        """Инициализация необходимых файлов"""
        # Файл ключей регионов
        if not os.path.exists(self.keys_path):
            default_keys = {
                "regions": {},
                "last_updated": None
            }
            self._save_json(self.keys_path, default_keys)

        # Файл кэша API
        if not os.path.exists(self.cache_path):
            default_cache = {
                "cache": {},
                "statistics": {
                    "total_requests": 0,
                    "cache_hits": 0
                }
            }
            self._save_json(self.cache_path, default_cache)

        # Файл для связи координат с регионами
        if not os.path.exists(self.coordinates_path):
            default_coords = {
                "coordinates_cache": {},
                "last_updated": None
            }
            self._save_json(self.coordinates_path, default_coords)

    def get_region_by_coordinates(self, latitude, longitude):
        """Определяет регион по координатам"""
        cache_key = f"{latitude:.4f}_{longitude:.4f}"
        coords_data = self._load_json(self.coordinates_path) or {"coordinates_cache": {}}

        # Проверяем кэш
        if cache_key in coords_data["coordinates_cache"]:
            cached = coords_data["coordinates_cache"][cache_key]
            if datetime.now().timestamp() - cached.get('timestamp', 0) < 30 * 24 * 3600:  # 30 дней
                return cached['region_name_ru'], cached['region_name_en']

        # Определяем регион через геокодинг
        try:
            location = self.geolocator.reverse((latitude, longitude), language='ru')
            if location and location.raw.get('address'):
                address = location.raw['address']

                # Пытаемся найти регион в адресе
                region_name_ru = (
                        address.get('state') or
                        address.get('region') or
                        address.get('county') or
                        "Неизвестный регион"
                )

                # Преобразуем в английское название
                region_name_en = self._translate_region_to_english(region_name_ru)

                # Сохраняем в кэш
                coords_data["coordinates_cache"][cache_key] = {
                    'region_name_ru': region_name_ru,
                    'region_name_en': region_name_en,
                    'timestamp': datetime.now().timestamp(),
                    'address': address
                }
                coords_data["last_updated"] = datetime.now().isoformat()
                self._save_json(self.coordinates_path, coords_data)

                return region_name_ru, region_name_en

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"⚠️ Ошибка геокодинга: {e}")

        return "Неизвестный регион", "unknown"

    def get_regions_statistics(self):
        """Получает статистику по всем сохраненным регионам"""
        regions_stats = {}
        all_regions = self.get_all_regions()

        for region_en, region_info in all_regions.items():
            region_data = self.get_region_data(region_en)
            if region_data:
                # Создаем DataFrame для анализа
                df = pd.DataFrame(region_data)

                # Статистика по классам
                class_stats = {}
                for animal_class in df['class_ru'].unique():
                    if animal_class and animal_class != 'Не указано':
                        count = len(df[df['class_ru'] == animal_class])
                        class_stats[animal_class] = count

                regions_stats[region_en] = {
                    'name_ru': region_info.get('name_ru', region_en),
                    'total_animals': len(region_data),
                    'unique_species': df['scientific_name'].nunique(),
                    'class_distribution': class_stats,
                    'last_updated': region_info.get('last_updated', 'Неизвестно')
                }

        return regions_stats

    def _translate_region_to_english(self, region_name_ru):
        """Переводит название региона на английский для GBIF"""
        russian_to_english = {
            'Республика Адыгея': 'Adygea',
            'Республика Алтай': 'Altai',
            'Алтайский край': 'Altai Krai',
            'Амурская область': 'Amur',
            'Архангельская область': 'Arkhangelsk',
            'Астраханская область': 'Astrakhan',
            'Республика Башкортостан': 'Bashkortostan',
            'Белгородская область': 'Belgorod',
            'Брянская область': 'Bryansk',
            'Республика Бурятия': 'Buryatia',
            'Чеченская Республика': 'Chechnya',
            'Челябинская область': 'Chelyabinsk',
            'Чукотский автономный округ': 'Chukotka',
            'Республика Крым': 'Crimea',
            'Республика Дагестан': 'Dagestan',
            'Республика Ингушетия': 'Ingushetia',
            'Иркутская область': 'Irkutsk',
            'Ивановская область': 'Ivanovo',
            'Еврейская автономная область': 'Jewish',
            'Кабардино-Балкарская Республика': 'Kabardino-Balkaria',
            'Калининградская область': 'Kaliningrad',
            'Республика Калмыкия': 'Kalmykia',
            'Калужская область': 'Kaluga',
            'Камчатский край': 'Kamchatka',
            'Карачаево-Черкесская Республика': 'Karachay-Cherkessia',
            'Республика Карелия': 'Karelia',
            'Кемеровская область': 'Kemerovo',
            'Хабаровский край': 'Khabarovsk',
            'Республика Хакасия': 'Khakassia',
            'Ханты-Мансийский автономный округ — Югра': 'Khanty-Mansi',
            'Кировская область': 'Kirov',
            'Коми Республика': 'Komi',
            'Костромская область': 'Kostroma',
            'Краснодарский край': 'Krasnodar',
            'Красноярский край': 'Krasnoyarsk',
            'Курганская область': 'Kurgan',
            'Курская область': 'Kursk',
            'Ленинградская область': 'Leningrad',
            'Липецкая область': 'Lipetsk',
            'Магаданская область': 'Magadan',
            'Республика Марий Эл': 'Mari El',
            'Республика Мордовия': 'Mordovia',
            'Московская область': 'Moscow',
            'Москва': 'Moscow City',
            'Мурманская область': 'Murmansk',
            'Ненецкий автономный округ': 'Nenets',
            'Нижегородская область': 'Nizhny Novgorod',
            'Новгородская область': 'Novgorod',
            'Новосибирская область': 'Novosibirsk',
            'Омская область': 'Omsk',
            'Оренбургская область': 'Orenburg',
            'Орловская область': 'Oryol',
            'Пензенская область': 'Penza',
            'Пермский край': 'Perm',
            'Приморский край': 'Primorsky',
            'Псковская область': 'Pskov',
            'Ростовская область': 'Rostov',
            'Рязанская область': 'Ryazan',
            'Санкт-Петербург': 'Saint Petersburg',
            'Республика Саха (Якутия)': 'Sakha',
            'Сахалинская область': 'Sakhalin',
            'Самарская область': 'Samara',
            'Саратовская область': 'Saratov',
            'Республика Северная Осетия — Алания': 'North Ossetia',
            'Смоленская область': 'Smolensk',
            'Ставропольский край': 'Stavropol',
            'Свердловская область': 'Sverdlovsk',
            'Тамбовская область': 'Tambov',
            'Республика Татарстан': 'Tatarstan',
            'Томская область': 'Tomsk',
            'Тульская область': 'Tula',
            'Республика Тыва': 'Tuva',
            'Тверская область': 'Tver',
            'Тюменская область': 'Tyumen',
            'Удмуртская Республика': 'Udmurtia',
            'Ульяновская область': 'Ulyanovsk',
            'Владимирская область': 'Vladimir',
            'Волгоградская область': 'Volgograd',
            'Вологодская область': 'Vologda',
            'Воронежская область': 'Voronezh',
            'Ямало-Ненецкий автономный округ': 'Yamalo-Nenets',
            'Ярославская область': 'Yaroslavl',
            'Забайкальский край': 'Zabaykalsky',
            'Донецкая Народная Республика': 'Donetsk',
            'Луганская Народная Республика': 'Luhansk',
            'Херсонская область': 'Kherson',
            'Запорожская область': 'Zaporozhye',
            'Севастополь': 'Sevastopol'
        }

        # Если точного совпадения нет, ищем частичное
        for ru_name, en_name in russian_to_english.items():
            if region_name_ru in ru_name or ru_name in region_name_ru:
                return en_name

        return region_name_ru.replace(' ', '').replace('область', 'Oblast').replace('край', 'Krai')

    def _get_region_filename(self, region_name_en):
        """Генерирует имя файла для региона"""
        return f"{region_name_en.lower()}.json"

    def _get_region_filepath(self, region_name_en):
        """Получает полный путь к файлу региона"""
        filename = self._get_region_filename(region_name_en)
        return os.path.join(self.regions_path, filename)

    def _generate_cache_key(self, params):
        """Генерирует ключ для кэша на основе параметров запроса"""
        param_string = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_string.encode()).hexdigest()

    def _save_json(self, filepath, data):
        """Сохраняет данные в JSON файл"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения {filepath}: {e}")
            return False

    def _load_json(self, filepath):
        """Загружает данные из JSON файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"❌ Ошибка загрузки {filepath}: {e}")
            return None

    def region_exists(self, region_name_en):
        """Проверяет, есть ли данные по региону"""
        filepath = self._get_region_filepath(region_name_en)
        return os.path.exists(filepath)

    def get_region_data(self, region_name_en):
        """Получает данные по региону"""
        filepath = self._get_region_filepath(region_name_en)
        data = self._load_json(filepath)
        if data and 'animals' in data:
            return data['animals']
        return []

    def get_region_metadata(self, region_name_en):
        """Получает метаданные региона"""
        filepath = self._get_region_filepath(region_name_en)
        data = self._load_json(filepath)
        return data.get('metadata', {}) if data else {}

    def save_region_data(self, region_name_en, region_name_ru, animal_data):
        """Сохраняет данные о животных региона"""
        region_data = {
            "metadata": {
                "region_name_ru": region_name_ru,
                "region_name_en": region_name_en,
                "last_updated": datetime.now().isoformat(),
                "total_records": len(animal_data),
                "unique_species": len(set([animal.get('scientific_name', '') for animal in animal_data]))
            },
            "animals": animal_data,
            "statistics": self._calculate_statistics(animal_data)
        }

        filepath = self._get_region_filepath(region_name_en)
        success = self._save_json(filepath, region_data)

        if success:
            self._update_region_keys(region_name_en, region_name_ru)

        return success

    def _calculate_statistics(self, animal_data):
        """Рассчитывает статистику по данным о животных"""
        if not animal_data:
            return {}

        try:
            df = pd.DataFrame(animal_data)

            stats = {
                "total_animals": len(animal_data),
                "unique_species": df['scientific_name'].nunique(),
                "class_distribution": df['class'].value_counts().to_dict(),
                "top_species": df['scientific_name'].value_counts().head(10).to_dict(),
                "records_by_year": self._extract_year_stats(animal_data)
            }

            return stats
        except Exception as e:
            print(f"⚠️ Ошибка при расчете статистики: {e}")
            return {}

    def _extract_year_stats(self, animal_data):
        """Извлекает статистику по годам"""
        year_counts = {}
        for animal in animal_data:
            event_date = animal.get('eventDate', '')
            if event_date and len(event_date) >= 4:
                year = event_date[:4]
                if year.isdigit():
                    year_counts[year] = year_counts.get(year, 0) + 1

        return dict(sorted(year_counts.items()))

    def _update_region_keys(self, region_name_en, region_name_ru):
        """Обновляет файл ключей регионов"""
        keys_data = self._load_json(self.keys_path) or {"regions": {}, "last_updated": None}

        keys_data["regions"][region_name_en] = {
            "name_ru": region_name_ru,
            "data_file": self._get_region_filename(region_name_en),
            "last_updated": datetime.now().isoformat()
        }
        keys_data["last_updated"] = datetime.now().isoformat()

        self._save_json(self.keys_path, keys_data)

    def get_all_regions(self):
        """Получает список всех доступных регионов"""
        keys_data = self._load_json(self.keys_path)
        return keys_data.get("regions", {}) if keys_data else {}

    def get_api_cache(self, params):
        """Получает данные из кэша API"""
        cache_data = self._load_json(self.cache_path) or {"cache": {},
                                                          "statistics": {"total_requests": 0, "cache_hits": 0}}

        cache_key = self._generate_cache_key(params)
        cached_item = cache_data["cache"].get(cache_key)

        # Обновляем статистику
        cache_data["statistics"]["total_requests"] = cache_data["statistics"].get("total_requests", 0) + 1

        if cached_item and self._is_cache_valid(cached_item):
            cache_data["statistics"]["cache_hits"] = cache_data["statistics"].get("cache_hits", 0) + 1
            self._save_json(self.cache_path, cache_data)
            return cached_item["data"]

        self._save_json(self.cache_path, cache_data)
        return None

    def save_api_cache(self, params, data, ttl_hours=24):
        """Сохраняет данные в кэш API"""
        cache_data = self._load_json(self.cache_path) or {"cache": {},
                                                          "statistics": {"total_requests": 0, "cache_hits": 0}}

        cache_key = self._generate_cache_key(params)
        cache_data["cache"][cache_key] = {
            "data": data,
            "created_at": datetime.now().isoformat(),
            "ttl_hours": ttl_hours
        }

        # Очищаем старый кэш
        cache_data["cache"] = self._clean_old_cache(cache_data["cache"])

        self._save_json(self.cache_path, cache_data)

    def _is_cache_valid(self, cached_item):
        """Проверяет валидность кэша"""
        try:
            created_at = datetime.fromisoformat(cached_item["created_at"])
            ttl = timedelta(hours=cached_item["ttl_hours"])
            return datetime.now() - created_at < ttl
        except:
            return False

    def _clean_old_cache(self, cache_dict):
        """Очищает просроченный кэш"""
        valid_cache = {}
        for key, item in cache_dict.items():
            if self._is_cache_valid(item):
                valid_cache[key] = item
        return valid_cache

    def get_cache_stats(self):
        """Получает статистику кэша"""
        cache_data = self._load_json(self.cache_path)
        if cache_data:
            return cache_data.get("statistics", {})
        return {}