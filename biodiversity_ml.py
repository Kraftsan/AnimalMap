import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report
import requests
import json
import os
import warnings
import folium
from folium.plugins import MarkerCluster, HeatMap
import branca.colormap as cm

warnings.filterwarnings('ignore')


class BiodiversityML:
    def __init__(self):
        self.base_path = "data"
        self.regions_path = os.path.join(self.base_path, "regions")
        self.config_path = "config"
        self.df = None
        self.features = None
        self.target = None
        self.model = None

    def load_regions_from_config(self):
        """Загружает список регионов из конфигурационных файлов"""
        print("Загрузка списка регионов из конфигурации...")

        regions_keys_path = os.path.join(self.config_path, "regions_keys.json")
        coordinates_path = os.path.join(self.config_path, "coordinates_regions.json")

        regions = {}

        # Загружаем regions_keys.json
        try:
            with open(regions_keys_path, 'r', encoding='utf-8') as f:
                regions_data = json.load(f)
                for region_en, region_info in regions_data.get('regions', {}).items():
                    regions[region_en] = {
                        'name_ru': region_info.get('name_ru', region_en),
                        'data_file': region_info.get('data_file'),
                        'last_updated': region_info.get('last_updated')
                    }
            print(f"Загружено {len(regions)} регионов из regions_keys.json")
        except Exception as e:
            print(f"Ошибка загрузки regions_keys.json: {e}")
            return {}

        # Обогащаем координатами из coordinates_regions.json
        try:
            with open(coordinates_path, 'r', encoding='utf-8') as f:
                coords_data = json.load(f)
                coordinates_cache = coords_data.get('coordinates_cache', {})

                for coord_key, coord_info in coordinates_cache.items():
                    region_name_ru = coord_info.get('region_name_ru')
                    # Находим регион по русскому названию
                    for region_en, region_data in regions.items():
                        if region_data['name_ru'] == region_name_ru:
                            # Извлекаем координаты из ключа
                            lat_lon = coord_key.split('_')
                            if len(lat_lon) == 2:
                                regions[region_en]['latitude'] = float(lat_lon[0])
                                regions[region_en]['longitude'] = float(lat_lon[1])
                            break
            print("Координаты регионов загружены")
        except Exception as e:
            print(f"Ошибка загрузки координат: {e}")

        return regions

    def get_real_region_data(self, region_name, data_file):
        """Получает реальные данные о животных региона из файла и извлекает координаты"""
        file_path = os.path.join(self.regions_path, data_file)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                region_data = json.load(f)

            animals_data = region_data.get('animals', [])
            statistics = region_data.get('statistics', {})
            metadata = region_data.get('metadata', {})

            if not animals_data:
                print(f"Нет данных о животных в файле {data_file}")
                return [], {}, {}, None, None

            print(f"Загружено {len(animals_data)} животных из {data_file}")

            # Извлекаем координаты из данных животных (берем средние координаты)
            latitudes = []
            longitudes = []

            for animal in animals_data:
                if 'decimalLatitude' in animal and animal['decimalLatitude'] is not None:
                    latitudes.append(animal['decimalLatitude'])
                if 'decimalLongitude' in animal and animal['decimalLongitude'] is not None:
                    longitudes.append(animal['decimalLongitude'])

            # Вычисляем средние координаты региона
            region_lat = np.mean(latitudes) if latitudes else None
            region_lon = np.mean(longitudes) if longitudes else None

            return animals_data, statistics, metadata, region_lat, region_lon

        except Exception as e:
            print(f"Ошибка загрузки файла {data_file}: {e}")
            return [], {}, {}, None, None

    def _analyze_region_biodiversity(self, animals_data, statistics, metadata):
        """Анализирует биоразнообразие региона на основе реальных данных"""
        if not animals_data:
            return {}

        df_animals = pd.DataFrame(animals_data)

        # Реальное распределение классов из данных
        class_distribution = df_animals['class'].value_counts()
        total_animals = len(animals_data)

        # Основные классы животных (используем фактические данные)
        mammal_species = len(
            df_animals[df_animals['class'].str.contains('Mammalia', na=False, case=False)]['scientific_name'].unique())
        bird_species = len(
            df_animals[df_animals['class'].str.contains('Aves', na=False, case=False)]['scientific_name'].unique())
        reptile_species = len(
            df_animals[df_animals['class'].str.contains('Reptilia', na=False, case=False)]['scientific_name'].unique())
        amphibian_species = len(
            df_animals[df_animals['class'].str.contains('Amphibia', na=False, case=False)]['scientific_name'].unique())
        fish_species = len(
            df_animals[df_animals['class'].str.contains('Actinopterygii|Chondrichthyes', na=False, case=False)][
                'scientific_name'].unique())
        insect_species = len(
            df_animals[df_animals['class'].str.contains('Insecta', na=False, case=False)]['scientific_name'].unique())

        # Другие классы
        other_species = len(df_animals[~df_animals['class'].str.contains(
            'Mammalia|Aves|Reptilia|Amphibia|Actinopterygii|Chondrichthyes|Insecta', na=False, case=False)][
                                'scientific_name'].unique())

        # Общее количество уникальных видов
        total_unique_species = df_animals['scientific_name'].nunique()

        # Анализ временного распределения из statistics
        records_by_year = statistics.get('records_by_year', {})
        recent_activity = self._analyze_temporal_activity(records_by_year)

        stats = {
            'total_species': total_unique_species,
            'total_records': total_animals,
            'mammal_species': mammal_species,
            'bird_species': bird_species,
            'reptile_species': reptile_species,
            'amphibian_species': amphibian_species,
            'fish_species': fish_species,
            'insect_species': insect_species,
            'other_species': other_species,
            'records_2020_2024': recent_activity.get('records_2020_2024', 0),
            'max_year_records': recent_activity.get('max_year_records', 0),
            'data_freshness': recent_activity.get('data_freshness', 0),
        }

        # Индекс разнообразия Шеннона на основе реальных классов
        if len(class_distribution) > 0:
            stats['shannon_diversity'] = self._calculate_shannon_diversity(class_distribution)

            # Доминирующий класс
            if len(class_distribution) > 0:
                stats['dominant_class'] = class_distribution.index[0]
                stats['dominant_class_ratio'] = class_distribution.iloc[0] / total_animals if total_animals > 0 else 0
        else:
            stats['shannon_diversity'] = 0
            stats['dominant_class'] = 'Неизвестно'
            stats['dominant_class_ratio'] = 0

        # Доля редких видов (встречаются 1 раз)
        species_counts = df_animals['scientific_name'].value_counts()
        rare_species = len(species_counts[species_counts == 1])
        stats['rare_species_ratio'] = rare_species / len(species_counts) if len(species_counts) > 0 else 0

        # Процентное распределение по основным классам
        if total_unique_species > 0:
            stats['mammal_ratio'] = mammal_species / total_unique_species
            stats['bird_ratio'] = bird_species / total_unique_species
            stats['reptile_ratio'] = reptile_species / total_unique_species
            stats['amphibian_ratio'] = amphibian_species / total_unique_species
            stats['fish_ratio'] = fish_species / total_unique_species
            stats['insect_ratio'] = insect_species / total_unique_species
            stats['other_ratio'] = other_species / total_unique_species
        else:
            stats.update(
                {f'{cls}_ratio': 0 for cls in ['mammal', 'bird', 'reptile', 'amphibian', 'fish', 'insect', 'other']})

        # Эффективность сбора данных (записей на вид)
        stats['records_per_species'] = total_animals / total_unique_species if total_unique_species > 0 else 0

        return stats

    def _analyze_temporal_activity(self, records_by_year):
        """Анализирует временную активность сбора данных"""
        if not records_by_year:
            return {}

        # Преобразуем годы в числа
        years = {int(year): count for year, count in records_by_year.items() if year.isdigit()}

        if not years:
            return {}

        # Активность за последние 5 лет
        current_year = 2025
        recent_years = [current_year - i for i in range(5)]
        records_2020_2024 = sum(years.get(year, 0) for year in recent_years)

        # Максимальная активность за год
        max_year_records = max(years.values()) if years else 0

        # Свежесть данных (год самой свежей записи)
        data_freshness = max(years.keys()) if years else 0

        return {
            'records_2020_2024': records_2020_2024,
            'max_year_records': max_year_records,
            'data_freshness': data_freshness
        }

    def _calculate_shannon_diversity(self, distribution):
        """Вычисляет индекс разнообразия Шеннона"""
        if len(distribution) == 0:
            return 0
        proportions = distribution / distribution.sum()
        return -np.sum(proportions * np.log(proportions + 1e-10))

    def collect_regional_data(self, use_api=False):
        """Собирает данные по всем регионам для ML анализа"""
        print("Сбор данных по регионам")

        all_regions_data = []
        regions = self.load_regions_from_config()
        processed_regions = set()  # Для отслеживания уже обработанных регионов

        if not regions:
            print("Не удалось загрузить список регионов")
            return pd.DataFrame()

        for region_en, region_info in regions.items():
            # Пропускаем дубликаты
            if region_en in processed_regions:
                print(f"Пропускаем дубликат региона: {region_info.get('name_ru', region_en)}")
                continue

            print(f"Обрабатываем регион: {region_info.get('name_ru', region_en)}")
            processed_regions.add(region_en)

            animals_data = []
            statistics = {}
            metadata = {}
            region_lat = region_info.get('latitude')
            region_lon = region_info.get('longitude')

            if use_api:
                # Используем API для получения данных
                animals_data = self.fetch_region_data_from_api(region_en, region_info['name_ru'])
            else:
                # Используем локальные файлы с латинскими названиями
                data_file = region_info.get('data_file')
                if data_file and os.path.exists(os.path.join(self.regions_path, data_file)):
                    animals_data, statistics, metadata, file_lat, file_lon = self.get_real_region_data(region_en,
                                                                                                       data_file)

                    # Используем координаты из файла, если они есть
                    if file_lat is not None and file_lon is not None:
                        region_lat = file_lat
                        region_lon = file_lon
                        print(f"  Координаты из файла: {region_lat:.4f}, {region_lon:.4f}")
                    else:
                        print(f"  Координаты не найдены в файле, используем из конфига")
                else:
                    print(f"Файл {data_file} не найден для региона {region_en}")

            if not animals_data:
                print(f"Нет данных для региона {region_en}")
                continue

            # Анализируем биоразнообразие региона на основе реальных данных
            biodiversity_stats = self._analyze_region_biodiversity(animals_data, statistics, metadata)

            # Добавляем информацию о регионе
            region_record = {
                'region_name': region_en,
                'region_name_ru': region_info.get('name_ru', region_en),
                'latitude': region_lat,
                'longitude': region_lon,
                **biodiversity_stats
            }

            all_regions_data.append(region_record)

        self.df = pd.DataFrame(all_regions_data)

        if len(self.df) == 0:
            print("Не удалось собрать данные ни по одному региону")
            return pd.DataFrame()
        else:
            print(f"Собраны реальные данные по {len(self.df)} регионам")

        return self.df

    def _add_default_coordinates(self):
        """Добавляет координаты по умолчанию для регионов без координат"""
        if self.df is None or len(self.df) == 0:
            return pd.DataFrame()

        df_clean = self.df.copy()

        # Координаты по умолчанию для основных регионов России
        default_coords = {
            'Amur': (53.0, 127.0),
            'Krasnodar': (45.0355, 38.9755),
            'Altai': (50.0, 86.0),
            'Altai Krai': (52.0, 83.0),
            'Buryatia': (52.0, 107.0),
            'Khabarovsk': (48.5, 135.0),
            'Primorsky': (43.0, 132.0),
            'Sakhalin': (50.0, 143.0),
            'Kamchatka': (56.0, 159.0),
            'Magadan': (60.0, 151.0)
        }

        for idx, row in df_clean.iterrows():
            if pd.isna(row['latitude']) or pd.isna(row['longitude']):
                region_name = row['region_name']
                if region_name in default_coords:
                    df_clean.at[idx, 'latitude'] = default_coords[region_name][0]
                    df_clean.at[idx, 'longitude'] = default_coords[region_name][1]
                    print(f"  Добавлены координаты по умолчанию для {region_name}")
                else:
                    # Удаляем регионы без координат
                    df_clean = df_clean.drop(idx)
                    print(f"  Удален регион {region_name} - нет координат")

        return df_clean

    def enrich_with_climate_data(self):
        """Обогащает данные климатической информацией"""
        print("🌍 Добавление климатических данных...")

        # Климатическая классификация регионов России (расширенная)
        climate_zones = {
            'Amur': 'continental',
            'Krasnodar': 'temperate_maritime',
            'Altai': 'continental',
            'Altai Krai': 'continental'
        }

        # Среднегодовая температура (примерные данные)
        avg_temperatures = {
            'Amur': -1.3, 'Krasnodar': 12.1, 'Altai': 0.0, 'Altai Krai': 1.0
        }

        self.df['climate_zone'] = self.df['region_name'].map(climate_zones).fillna('temperate_continental')
        self.df['avg_temperature'] = self.df['region_name'].map(avg_temperatures).fillna(5.0)

        # Если нет координат, используем приблизительные на основе известных данных
        if 'latitude' not in self.df.columns or self.df['latitude'].isna().any():
            default_coords = {
                'Amur': 53.0, 'Krasnodar': 45.0355, 'Altai': 50.0, 'Altai Krai': 52.0
            }
            self.df['latitude'] = self.df['region_name'].map(default_coords).fillna(55.0)

        print("Климатические данные добавлены")
        return self.df

    def create_ml_features(self):
        """Создает признаки для машинного обучения на основе реальных данных"""
        print("Подготовка признаков")

        # При малом количестве регионов используем только 2 класса
        if len(self.df) < 5:
            # Используем медиану для 2 классов
            median_species = self.df['total_species'].median()
            self.df['biodiversity_class'] = np.where(
                self.df['total_species'] > median_species, 'high', 'low'
            )
            print("Используем 2 классов из-за малого количества регионов")
        else:
            # Используем квартили для 3 классов
            species_quantiles = self.df['total_species'].quantile([0.33, 0.66])
            self.df['biodiversity_class'] = pd.cut(
                self.df['total_species'],
                bins=[0, species_quantiles[0.33], species_quantiles[0.66], float('inf')],
                labels=['low', 'medium', 'high']
            )

        # Основные признаки из реальных данных
        features = [
            'total_species', 'total_records', 'mammal_species', 'bird_species',
            'reptile_species', 'amphibian_species', 'fish_species', 'insect_species', 'other_species',
            'shannon_diversity', 'rare_species_ratio', 'dominant_class_ratio',
            'mammal_ratio', 'bird_ratio', 'reptile_ratio', 'amphibian_ratio',
            'fish_ratio', 'insect_ratio', 'other_ratio',
            'records_per_species', 'records_2020_2024', 'max_year_records', 'data_freshness',
            'latitude', 'avg_temperature'
        ]

        # One-hot encoding для климатических зон
        climate_dummies = pd.get_dummies(self.df['climate_zone'], prefix='climate')

        self.features = pd.concat([
            self.df[features].fillna(0),
            climate_dummies
        ], axis=1)

        self.target = self.df['biodiversity_class']

        print(f"Создано {len(self.features.columns)} признаков из реальных данных")
        print(f"Распределение классов биоразнообразия: {self.target.value_counts().to_dict()}")

        return self.features, self.target

    def train_biodiversity_model(self):
        """Обучает модель классификации биоразнообразия"""
        print("Обучение модели")

        if len(self.df) < 2:
            print("Недостаточно данных для обучения модели")
            return None

        # Проверяем баланс классов
        class_counts = self.target.value_counts()
        print(f"Баланс классов: {class_counts.to_dict()}")

        # При малом количестве данных используем упрощенное разделение
        if len(self.df) <= 3 or class_counts.min() < 2:
            print("Мало данных для разделения - используем упрощенное обучение")
            # Обучаем на всех данных
            X_train, X_test, y_train, y_test = self.features, self.features, self.target, self.target
        else:
            # Разделяем данные с проверкой на стратификацию
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    self.features, self.target, test_size=0.3, random_state=42, stratify=self.target
                )
            except ValueError:
                # Если стратификация невозможна, используем обычное разделение
                print("Стратификация невозможна - используем обычное разделение")
                X_train, X_test, y_train, y_test = train_test_split(
                    self.features, self.target, test_size=0.3, random_state=42
                )

        # Обучаем модель
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42,
            class_weight='balanced'
        )

        self.model.fit(X_train, y_train)

        # Оценка модели
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        print(f"Модель обучена!")
        print(f"Accuracy на обучении: {train_score:.3f}")
        print(f"Accuracy на тесте: {test_score:.3f}")

        # Детальная оценка (только если есть тестовые данные)
        if len(X_test) > 0:
            y_pred = self.model.predict(X_test)
            print(f"\nДетальная оценка модели:")
            print(classification_report(y_test, y_pred))

        # Безопасная кросс-валидация
        if len(self.df) >= 3:
            n_folds = min(3, len(self.df))
            try:
                cv_scores = cross_val_score(self.model, self.features, self.target, cv=n_folds)
                print(f"Кросс-валидация ({n_folds} фолда): {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
            except Exception as e:
                print(f"Кросс-валидация невозможна: {e}")

        return self.model

    def analyze_feature_importance(self):
        """Анализирует важность признаков"""
        if self.model is None:
            print("Модель не обучена")
            return

        feature_importance = pd.DataFrame({
            'feature': self.features.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print("\nВАЖНОСТЬ ПРИЗНАКОВ:")
        print("=" * 50)
        for i, row in feature_importance.head(15).iterrows():
            print(f"{row['feature']:30} {row['importance']:.4f}")

        # Визуализация (без сохранения в файл)
        plt.figure(figsize=(12, 8))
        top_features = feature_importance.head(15)
        sns.barplot(data=top_features, x='importance', y='feature', palette='viridis')
        plt.title('Важность признаков для прогноза биоразнообразия\n(на основе реальных данных)',
                  fontsize=14, fontweight='bold')
        plt.xlabel('Важность признака')
        plt.tight_layout()
        plt.show()

        return feature_importance

    def show_detailed_analysis(self):
        """Показывает детальный анализ данных с учетом временных характеристик"""
        print("\nДЕТАЛЬНЫЙ АНАЛИЗ РЕАЛЬНЫХ ДАННЫХ:")
        print("=" * 60)

        if self.df is None or len(self.df) == 0:
            print("Нет данных для анализа")
            return

        # Основная статистика
        print(f"ОБЩАЯ СТАТИСТИКА:")
        print(f"   • Количество регионов: {len(self.df)}")
        print(f"   • Среднее количество видов: {self.df['total_species'].mean():.1f}")
        print(f"   • Среднее количество записей: {self.df['total_records'].mean():.0f}")
        print(f"   • Эффективность сбора: {self.df['records_per_species'].mean():.1f} записей/вид")

        # Временные характеристики
        print(f"\nВРЕМЕННЫЕ ХАРАКТЕРИСТИКИ:")
        print(f"   • Средняя активность (2020-2024): {self.df['records_2020_2024'].mean():.0f} записей")
        print(f"   • Максимальная активность за год: {self.df['max_year_records'].max()} записей")
        print(f"   • Свежесть данных: до {int(self.df['data_freshness'].max())} года")

        # Распределение по классам животных
        print(f"\nРАСПРЕДЕЛЕНИЕ ПО КЛАССАМ ЖИВОТНЫХ:")
        class_totals = {
            'Млекопитающие': self.df['mammal_species'].sum(),
            'Птицы': self.df['bird_species'].sum(),
            'Пресмыкающиеся': self.df['reptile_species'].sum(),
            'Земноводные': self.df['amphibian_species'].sum(),
            'Рыбы': self.df['fish_species'].sum(),
            'Насекомые': self.df['insect_species'].sum(),
            'Другие': self.df['other_species'].sum()
        }

        total_all_species = sum(class_totals.values())
        for class_name, total in class_totals.items():
            percentage = (total / total_all_species) * 100 if total_all_species > 0 else 0
            print(f"   • {class_name}: {total} видов ({percentage:.1f}%)")

        # Визуализация
        self._create_detailed_visualizations()

    def _create_detailed_visualizations(self):
        """Создает детальные визуализации данных"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Сравнение видов и записей
        regions = self.df['region_name_ru']
        x = np.arange(len(regions))
        width = 0.35

        ax1.bar(x - width / 2, self.df['total_species'], width, label='Уникальные виды', alpha=0.7)
        ax1.bar(x + width / 2, self.df['total_records'] / 10, width, label='Все записи (÷10)', alpha=0.7)
        ax1.set_title('Сравнение уникальных видов и общего количества записей', fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(regions, rotation=45, ha='right')
        ax1.legend()
        ax1.set_ylabel('Количество')

        # 2. Эффективность сбора данных
        ax2.bar(regions, self.df['records_per_species'], color='orange', alpha=0.7)
        ax2.set_title('Эффективность сбора данных (записей на вид)', fontweight='bold')
        ax2.set_xticklabels(regions, rotation=45, ha='right')
        ax2.set_ylabel('Записей на вид')

        # 3. Активность в последние годы
        ax3.bar(regions, self.df['records_2020_2024'], color='green', alpha=0.7)
        ax3.set_title('Активность сбора данных (2020-2024)', fontweight='bold')
        ax3.set_xticklabels(regions, rotation=45, ha='right')
        ax3.set_ylabel('Количество записей')

        # 4. Распределение по классам (все регионы)
        class_columns = ['mammal_species', 'bird_species', 'insect_species', 'other_species']
        class_labels = ['Млекопитающие', 'Птицы', 'Насекомые', 'Другие']

        bottom = np.zeros(len(self.df))
        for i, col in enumerate(class_columns):
            ax4.bar(self.df['region_name_ru'], self.df[col], label=class_labels[i], bottom=bottom, alpha=0.7)
            bottom += self.df[col]

        ax4.set_title('Состав биоразнообразия по регионам', fontweight='bold')
        ax4.set_xticklabels(self.df['region_name_ru'], rotation=45, ha='right')
        ax4.legend()
        ax4.set_ylabel('Количество видов')

        plt.tight_layout()
        plt.show()

    def make_predictions(self):
        """Делает прогнозы на основе обученной модели"""
        print("\nДЕМОНСТРАЦИЯ ПРОГНОЗОВ:")
        print("=" * 40)

        if self.model is None:
            print("Модель не обучена!")
            return

        # Прогноз для среднего региона
        avg_features = self.features.mean().to_frame().T
        avg_pred = self.model.predict(avg_features)[0]
        avg_prob = self.model.predict_proba(avg_features)[0]

        print(f"Прогноз для региона со средними характеристиками:")
        print(f"   Класс биоразнообразия: {avg_pred}")
        print(f"   Вероятности: {dict(zip(self.model.classes_, [f'{p:.3f}' for p in avg_prob]))}")

        # Анализ влияния признаков
        print(f"\nКлючевые факторы биоразнообразия:")
        feature_importance = pd.DataFrame({
            'feature': self.features.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        top_factors = feature_importance.head(5)
        for _, row in top_factors.iterrows():
            print(f"   • {row['feature']}: {row['importance']:.3f}")

    def create_biodiversity_map(self, save_path="biodiversity_map.html"):
        """Создает интерактивную карту биоразнообразия регионов"""
        print("🗺️ Создание карты биоразнообразия...")

        if self.df is None or len(self.df) == 0:
            print("Нет данных для создания карты")
            return None

        # Проверяем и очищаем данные от NaN в координатах
        df_clean = self.df.dropna(subset=['latitude', 'longitude']).copy()

        if len(df_clean) == 0:
            print("❌ Нет валидных координат для создания карты")
            # Попробуем добавить координаты по умолчанию
            df_clean = self._add_default_coordinates()
            if len(df_clean) == 0:
                print("❌ Не удалось получить координаты для карты")
                return None

        print(f"✅ Используем {len(df_clean)} регионов с валидными координатами")

        # Создаем цветовую шкалу на основе общего количества видов
        if 'total_species' in df_clean.columns:
            species_values = df_clean['total_species']
        else:
            species_values = df_clean['total_records']

        max_species = species_values.max()
        min_species = species_values.min()

        print(f"📊 Диапазон видов: {min_species} - {max_species}")

        # Создаем цветовую шкалу (зеленая палитра для биоразнообразия)
        colormap = cm.LinearColormap(
            colors=['#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#bd0026'],
            vmin=min_species,
            vmax=max_species,
            caption='Количество видов'
        )

        # Определяем центр карты (средние координаты всех регионов)
        center_lat = df_clean['latitude'].mean()
        center_lon = df_clean['longitude'].mean()

        print(f"📍 Центр карты: {center_lat:.4f}, {center_lon:.4f}")

        # Создаем карту
        biodiversity_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=4,
            tiles='OpenStreetMap'
        )

        # Добавляем кластер маркеров для лучшей визуализации
        marker_cluster = MarkerCluster().add_to(biodiversity_map)

        # Добавляем маркеры для каждого региона
        for _, region in df_clean.iterrows():
            # Определяем цвет маркера на основе количества видов
            if 'total_species' in region:
                species_count = region['total_species']
            else:
                species_count = region['total_records']

            color = colormap(species_count)

            # Создаем всплывающее окно с информацией
            popup_text = f"""
            <div style="width: 280px;">
                <h4>{region['region_name_ru']}</h4>
                <hr style="margin: 5px 0;">
                <b>Биоразнообразие:</b><br>
                • Всего видов: <b>{region.get('total_species', 'N/A')}</b><br>
                • Всего записей: <b>{region.get('total_records', 'N/A')}</b><br>
                • Класс: <b>{region.get('biodiversity_class', 'N/A')}</b><br>
                <br>
                <b>Распределение:</b><br>
                • Млекопитающие: {region.get('mammal_species', 0)}<br>
                • Птицы: {region.get('bird_species', 0)}<br>
                • Насекомые: {region.get('insect_species', 0)}<br>
                • Другие: {region.get('other_species', 0)}<br>
                <br>
                <b>Активность:</b><br>
                • Записей (2020-2024): {region.get('records_2020_2024', 0)}<br>
                • Эффективность: {region.get('records_per_species', 0):.1f} зап./вид<br>
                <br>
                <small>Координаты: {region['latitude']:.4f}, {region['longitude']:.4f}</small>
            </div>
            """

            # Добавляем маркер на карту
            folium.CircleMarker(
                location=[region['latitude'], region['longitude']],
                radius=15 + (species_count / max_species * 20) if max_species > 0 else 15,
                popup=folium.Popup(popup_text, max_width=300),
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2,
                tooltip=f"{region['region_name_ru']}: {species_count} видов"
            ).add_to(marker_cluster)

        # Добавляем цветовую шкалу на карту
        colormap.add_to(biodiversity_map)

        # Добавляем слой с тепловой картой
        try:
            # Создаем данные для тепловой карты
            heat_data = []
            for _, region in df_clean.iterrows():
                if 'total_species' in region:
                    weight = region['total_species'] / max_species if max_species > 0 else 0.5
                else:
                    weight = region['total_records'] / max_species if max_species > 0 else 0.5

                heat_data.append([region['latitude'], region['longitude'], weight])

            HeatMap(heat_data, radius=25, blur=15, max_zoom=10,
                    gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}).add_to(biodiversity_map)

        except Exception as e:
            print(f"⚠️ Не удалось создать тепловую карту: {e}")

        # Сохраняем карту
        biodiversity_map.save(save_path)
        print(f"✅ Карта сохранена как: {save_path}")

        # Показываем карту в Jupyter (если используется)
        try:
            from IPython.display import display
            display(biodiversity_map)
        except ImportError:
            print(f"📁 Файл карты сохранен: {save_path}")
            print("📌 Откройте файл в браузере для просмотра интерактивной карты")

        return biodiversity_map

    def create_comparison_maps(self):
        """Создает серию сравнительных карт"""
        print("🔄 Создание сравнительных карт...")

        if self.df is None or len(self.df) == 0:
            return

        # Карта 1: Общее биоразнообразие
        self.create_biodiversity_map("biodiversity_species_map.html")

        # Карта 2: Активность исследований
        if 'records_2020_2024' in self.df.columns:
            activity_map = folium.Map(
                location=[self.df['latitude'].mean(), self.df['longitude'].mean()],
                zoom_start=4
            )

            activity_colormap = cm.LinearColormap(
                colors=['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'],
                vmin=self.df['records_2020_2024'].min(),
                vmax=self.df['records_2020_2024'].max(),
                caption='Активность исследований (2020-2024)'
            )

            for _, region in self.df.iterrows():
                popup_text = f"""
                <b>{region['region_name_ru']}</b><br>
                Активность: {region['records_2020_2024']} записей<br>
                Всего видов: {region.get('total_species', 'N/A')}
                """

                folium.CircleMarker(
                    location=[region['latitude'], region['longitude']],
                    radius=10 + (region['records_2020_2024'] / self.df['records_2020_2024'].max() * 20),
                    popup=folium.Popup(popup_text, max_width=250),
                    color=activity_colormap(region['records_2020_2024']),
                    fill=True,
                    fillOpacity=0.7
                ).add_to(activity_map)

            activity_colormap.add_to(activity_map)
            activity_map.save("research_activity_map.html")
            print("✅ Карта активности исследований сохранена")


def main():
    """Основная функция с созданием карт"""
    print("ЗАПУСК АНАЛИЗА БИОРАЗНООБРАЗИЯ С КАРТАМИ")
    print("=" * 60)

    ml_analyzer = BiodiversityML()

    try:
        # 1. Сбор реальных данных из файлов
        df = ml_analyzer.collect_regional_data(use_api=False)

        if len(df) == 0:
            print("Не удалось собрать данные. Пробуем использовать API...")
            df = ml_analyzer.collect_regional_data(use_api=True)

        if len(df) == 0:
            print("Не удалось собрать данные ни из файлов, ни через API")
            return

        print(f"\nОСНОВНЫЕ ХАРАКТЕРИСТИКИ РЕГИОНОВ:")
        display_columns = ['region_name_ru', 'total_species', 'total_records', 'records_per_species',
                           'records_2020_2024']
        print(df[display_columns].to_string())

        # 2. Обогащение климатическими данными
        ml_analyzer.enrich_with_climate_data()

        # 3. Подготовка ML признаков
        features, target = ml_analyzer.create_ml_features()

        # 4. Детальный анализ данных
        ml_analyzer.show_detailed_analysis()

        # 5. СОЗДАНИЕ КАРТ БИОРАЗНООБРАЗИЯ
        print("\n🌍 СОЗДАНИЕ ВИЗУАЛИЗАЦИЙ НА КАРТЕ:")
        ml_analyzer.create_biodiversity_map()
        ml_analyzer.create_comparison_maps()

        # 6. Обучение модели
        model = ml_analyzer.train_biodiversity_model()

        if model is not None:
            # 7. Анализ важности признаков
            ml_analyzer.analyze_feature_importance()

            # 8. Прогнозы
            ml_analyzer.make_predictions()

            print("\n" + "=" * 60)
            print("АНАЛИЗ НА РЕАЛЬНЫХ ДАННЫХ УСПЕШНО ЗАВЕРШЕН!")
            print("📊 Созданы интерактивные карты биоразнообразия")
            print("=" * 60)

        else:
            print("\n⚠️ Модель не была обучена из-за недостатка данных")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()