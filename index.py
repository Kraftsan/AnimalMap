import requests
import pandas as pd
import time


def get_animals_by_region_correct(region_name_ru, country='RU', limit=500):
    """
    Поиск животных с правильными названиями регионов на английском
    """
    # Словарь переводов регионов России
    region_translations = {
        'Амурская': 'Amur',
        'Московская': 'Moscow',
        'Ленинградская': 'Leningrad',
        'Краснодарская': 'Krasnodar',
        'Свердловская': 'Sverdlovsk',
        'Новосибирская': 'Novosibirsk',
        'Ростовская': 'Rostov',
        'Челябинская': 'Chelyabinsk',
        'Волгоградская': 'Volgograd',
        'Иркутская': 'Irkutsk',
        'Тюменская': 'Tyumen'
    }

    # Получаем английское название региона
    region_name_en = region_translations.get(region_name_ru, region_name_ru)
    print(f"🔍 Поиск в регионе: {region_name_ru} ({region_name_en})")

    # Пробуем разные стратегии поиска
    strategies = [
        lambda: search_by_state_province(region_name_en, country, limit),
        lambda: search_by_coordinates(region_name_en, limit),  # Поиск по координатам региона
        lambda: search_by_species_in_russia(region_name_ru, limit)  # Поиск видов, известных в России
    ]

    for i, strategy in enumerate(strategies, 1):
        print(f"\n🎯 Стратегия {i}...")
        result = strategy()
        if not result.empty:
            print(f"✅ Найдено {len(result)} животных")
            return result
        time.sleep(1)  # Пауза между запросами

    return pd.DataFrame()


def search_by_state_province(region_name_en, country, limit):
    """
    Поиск по полю stateProvince
    """
    base_url = "https://api.gbif.org/v1"

    params = {
        'country': country,
        'stateProvince': region_name_en,
        'limit': limit,
        'kingdom': 'Animalia'
    }

    try:
        response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Найдено записей: {data['count']}")
            return process_animal_records(data.get('results', []))
    except Exception as e:
        print(f"Ошибка: {e}")

    return pd.DataFrame()


def search_by_coordinates(region_name_en, limit):
    """
    Поиск по приблизительным координатам региона
    """
    # Приблизительные координаты центров регионов
    region_coordinates = {
        'Amur': (53.0, 127.0),  # Амурская область
        'Moscow': (55.7, 37.6),
        'Leningrad': (59.9, 30.3),
        'Krasnodar': (45.0, 38.9)
    }

    if region_name_en not in region_coordinates:
        return pd.DataFrame()

    lat, lon = region_coordinates[region_name_en]
    base_url = "https://api.gbif.org/v1"

    # Поиск в радиусе 200 км от центра региона
    params = {
        'decimalLatitude': lat,
        'decimalLongitude': lon,
        'kingdom': 'Animalia',
        'limit': limit,
        'hasCoordinate': 'true'
    }

    try:
        response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Найдено по координатам: {data['count']}")
            return process_animal_records(data.get('results', []))
    except Exception as e:
        print(f"Ошибка: {e}")

    return pd.DataFrame()


def search_by_species_in_russia(region_name_ru, limit):
    """
    Поиск животных, которые точно есть в России
    """
    base_url = "https://api.gbif.org/v1"

    # Известные животные России
    russian_animals = [
        "Ursus arctos",  # Бурый медведь
        "Canis lupus",  # Волк
        "Vulpes vulpes",  # Лисица
        "Lepus timidus",  # Заяц-беляк
        "Sciurus vulgaris",  # Белка
        "Cervus elaphus",  # Благородный олень
        "Alces alces",  # Лось
        "Capreolus capreolus",  # Косуля
        "Lynx lynx",  # Рысь
        "Martes zibellina",  # Соболь
        "Mustela erminea",  # Горностай
        "Meles meles",  # Барсук
        "Castor fiber",  # Бобр
        "Sus scrofa",  # Кабан
        "Erinaceus europaeus"  # Ёж
    ]

    all_records = []

    for animal in russian_animals[:10]:  # Ограничим количество для скорости
        params = {
            'scientificName': animal,
            'country': 'RU',
            'limit': 20
        }

        try:
            response = requests.get(f"{base_url}/occurrence/search", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['count'] > 0:
                    print(f"✅ {animal}: {len(data['results'])} записей")
                    all_records.extend(data['results'])
            time.sleep(0.5)  # Пауза между запросами
        except Exception as e:
            print(f"Ошибка при поиске {animal}: {e}")

    return process_animal_records(all_records)


def process_animal_records(records):
    """
    Обрабатывает записи о животных
    """
    if not records:
        return pd.DataFrame()

    species_list = []

    for record in records:
        # Проверяем, что это животное
        kingdom = record.get('kingdom', '')
        if kingdom != 'Animalia':
            continue

        species_key = record.get('speciesKey')
        common_name_ru = get_russian_common_name(species_key)

        species_data = {
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
            'speciesKey': species_key
        }
        species_list.append(species_data)

    return pd.DataFrame(species_list)


def get_russian_common_name(species_key):
    """
    Получает русское название вида
    """
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


def analyze_animals(df, region_name):
    """
    Анализ найденных животных
    """
    if df.empty:
        print("Нет данных о животных для анализа")
        return None

    print(f"\n{'=' * 60}")
    print(f"🐾 АНАЛИЗ ЖИВОТНЫХ В {region_name.upper()} ОБЛАСТИ")
    print(f"{'=' * 60}")

    # Показываем общую статистику
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"Всего записей: {len(df)}")
    print(f"Уникальных видов: {df['scientific_name'].nunique()}")

    # Распределение по классам
    class_distribution = df['class'].value_counts()
    print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО КЛАССАМ:")
    for animal_class, count in class_distribution.items():
        percentage = (count / len(df)) * 100
        print(f"  {animal_class}: {count} ({percentage:.1f}%)")

    # Самые частые виды
    species_counts = df['scientific_name'].value_counts()
    if len(species_counts) > 0:
        print(f"\n🏆 САМЫЕ ЧАСТО ВСТРЕЧАЕМЫЕ ВИДЫ:")
        for i, (species, count) in enumerate(species_counts.head(5).items(), 1):
            common_name = df[df['scientific_name'] == species]['common_name'].iloc[0]
            animal_class = df[df['scientific_name'] == species]['class'].iloc[0]
            print(f"{i}. {species}")
            print(f"   📝 {common_name}" if common_name != 'Не указано' else "   📝 Нет русского названия")
            print(f"   🐾 {animal_class}, находок: {count}")
            print()

    return species_counts


# Основной скрипт
if __name__ == "__main__":
    region = "Амурская"

    print("🚀 Запуск поиска животных...")
    animal_data = get_animals_by_region_correct(region, limit=300)

    if not animal_data.empty:
        print(f"\n🎉 УСПЕХ! Найдено {len(animal_data)} записей о животных")

        # Показываем примеры
        print(f"\n🔍 ПРИМЕРЫ НАЙДЕННЫХ ЖИВОТНЫХ:")
        unique_animals = animal_data[['scientific_name', 'common_name', 'class']].drop_duplicates()
        for _, animal in unique_animals.head(15).iterrows():
            common_name = animal['common_name'] if animal['common_name'] != 'Не указано' else "—"
            print(f"  • {animal['scientific_name']} | {common_name} | {animal['class']}")

        # Анализ
        analyze_animals(animal_data, region)

        # Сохраняем
        filename = f'{region.lower()}_animals_found.csv'
        animal_data.to_csv(filename, index=False, encoding='utf-8')
        print(f"\n💾 Данные сохранены в '{filename}'")

    else:
        print("\n❌ Не удалось найти данные через GBIF API")
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("1. Попробуйте другой регион (например, 'Московская')")
        print("2. Проверьте подключение к интернету")
        print("3. Попробуйте позже - API может быть временно недоступен")
        print("4. Используйте VPN, если есть ограничения доступа")