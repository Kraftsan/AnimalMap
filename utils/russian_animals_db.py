import json
import os


class RussianAnimalsDB:
    def __init__(self, db_path="data/russian_animals.json"):
        self.db_path = db_path
        self.animals_db = self._load_database()

    def _load_database(self):
        """Загружает базу данных русских животных"""
        default_db = {
            "млекопитающие": [
                {"scientific_name": "Ursus arctos", "common_name": "Бурый медведь", "regions": ["все"]},
                {"scientific_name": "Canis lupus", "common_name": "Волк", "regions": ["все"]},
                {"scientific_name": "Vulpes vulpes", "common_name": "Обыкновенная лисица", "regions": ["все"]},
                {"scientific_name": "Lepus timidus", "common_name": "Заяц-беляк", "regions": ["все"]},
                {"scientific_name": "Sciurus vulgaris", "common_name": "Обыкновенная белка", "regions": ["все"]},
                {"scientific_name": "Alces alces", "common_name": "Лось", "regions": ["все"]},
                {"scientific_name": "Capreolus pygargus", "common_name": "Сибирская косуля",
                 "regions": ["Сибирь", "Дальний Восток"]},
                {"scientific_name": "Cervus elaphus", "common_name": "Благородный олень", "regions": ["все"]},
                {"scientific_name": "Lynx lynx", "common_name": "Обыкновенная рысь", "regions": ["все"]},
                {"scientific_name": "Martes zibellina", "common_name": "Соболь",
                 "regions": ["Сибирь", "Дальний Восток"]},
                {"scientific_name": "Mustela erminea", "common_name": "Горностай", "regions": ["все"]},
                {"scientific_name": "Meles meles", "common_name": "Барсук", "regions": ["все"]},
                {"scientific_name": "Castor fiber", "common_name": "Обыкновенный бобр", "regions": ["все"]},
                {"scientific_name": "Sus scrofa", "common_name": "Кабан", "regions": ["все"]},
                {"scientific_name": "Erinaceus europaeus", "common_name": "Обыкновенный ёж",
                 "regions": ["Европейская часть"]},
                {"scientific_name": "Lutra lutra", "common_name": "Речная выдра", "regions": ["все"]},
                {"scientific_name": "Gulo gulo", "common_name": "Росомаха", "regions": ["Сибирь", "Дальний Восток"]}
            ],
            "птицы": [
                {"scientific_name": "Tetrao urogallus", "common_name": "Глухарь", "regions": ["все"]},
                {"scientific_name": "Lyrurus tetrix", "common_name": "Тетерев", "regions": ["все"]},
                {"scientific_name": "Lagopus lagopus", "common_name": "Белая куропатка", "regions": ["все"]},
                {"scientific_name": "Aquila chrysaetos", "common_name": "Беркут", "regions": ["все"]},
                {"scientific_name": "Buteo buteo", "common_name": "Обыкновенный канюк", "regions": ["все"]},
                {"scientific_name": "Strix uralensis", "common_name": "Длиннохвостая неясыть", "regions": ["все"]},
                {"scientific_name": "Corvus corax", "common_name": "Ворон", "regions": ["все"]},
                {"scientific_name": "Pica pica", "common_name": "Сорока", "regions": ["все"]},
                {"scientific_name": "Garrulus glandarius", "common_name": "Сойка", "regions": ["все"]},
                {"scientific_name": "Parus major", "common_name": "Большая синица", "regions": ["все"]}
            ],
            "рептилии": [
                {"scientific_name": "Lacerta agilis", "common_name": "Прыткая ящерица", "regions": ["все"]},
                {"scientific_name": "Natrix natrix", "common_name": "Обыкновенный уж", "regions": ["все"]},
                {"scientific_name": "Vipera berus", "common_name": "Обыкновенная гадюка", "regions": ["все"]},
                {"scientific_name": "Anguis fragilis", "common_name": "Ломкая веретеница",
                 "regions": ["Европейская часть"]}
            ],
            "амфибии": [
                {"scientific_name": "Rana temporaria", "common_name": "Травяная лягушка", "regions": ["все"]},
                {"scientific_name": "Bufo bufo", "common_name": "Серая жаба", "regions": ["все"]},
                {"scientific_name": "Triturus cristatus", "common_name": "Гребенчатый тритон",
                 "regions": ["Европейская часть"]},
                {"scientific_name": "Bombina bombina", "common_name": "Краснобрюхая жерлянка",
                 "regions": ["Европейская часть"]}
            ],
            "рыбы": [
                {"scientific_name": "Esox lucius", "common_name": "Обыкновенная щука", "regions": ["все"]},
                {"scientific_name": "Perca fluviatilis", "common_name": "Речной окунь", "regions": ["все"]},
                {"scientific_name": "Cyprinus carpio", "common_name": "Сазан", "regions": ["все"]},
                {"scientific_name": "Carassius carassius", "common_name": "Золотой карась", "regions": ["все"]}
            ]
        }

        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем файл если его нет
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                with open(self.db_path, 'w', encoding='utf-8') as f:
                    json.dump(default_db, f, ensure_ascii=False, indent=2)
                return default_db
        except:
            return default_db

    def get_animals_by_region(self, region_name_ru):
        """Получает животных для региона из базы данных"""
        region_keywords = self._get_region_keywords(region_name_ru)
        animals = []

        for category, species_list in self.animals_db.items():
            for animal in species_list:
                if self._is_animal_in_region(animal, region_keywords):
                    animals.append({
                        'scientific_name': animal['scientific_name'],
                        'common_name': animal['common_name'],
                        'class_ru': category.capitalize(),
                        'phylum_ru': 'Хордовые',
                        'source': 'local_db',
                        'region': region_name_ru
                    })

        return animals

    def _get_region_keywords(self, region_name_ru):
        """Определяет ключевые слова для региона"""
        region_mapping = {
            'Забайкальский край': ['Сибирь', 'Дальний Восток', 'все'],
            'Амурская': ['Дальний Восток', 'все'],
            'Краснодарский край': ['Европейская часть', 'все'],
            'Москва': ['Европейская часть', 'все'],
            'Крым': ['Европейская часть', 'все'],
            'Татарстан': ['Европейская часть', 'все']
        }

        return region_mapping.get(region_name_ru, ['все'])

    def _is_animal_in_region(self, animal, region_keywords):
        """Проверяет, водится ли животное в регионе"""
        return any(keyword in animal['regions'] for keyword in region_keywords)

    def get_common_name(self, scientific_name):
        """Получает русское название по научному"""
        for category, species_list in self.animals_db.items():
            for animal in species_list:
                if animal['scientific_name'].lower() == scientific_name.lower():
                    return animal['common_name']
        return None

    def enhance_gbif_data(self, gbif_animals):
        """Улучшает данные из GBIF русскими названиями"""
        enhanced_animals = []

        for animal in gbif_animals:
            enhanced_animal = animal.copy()
            scientific_name = animal.get('scientific_name')

            # Если нет русского названия, ищем в базе
            if scientific_name and (not animal.get('common_name') or animal.get('common_name') == 'Не указано'):
                common_name = self.get_common_name(scientific_name)
                if common_name:
                    enhanced_animal['common_name'] = common_name
                    enhanced_animal['name_source'] = 'local_db'

            enhanced_animals.append(enhanced_animal)

        return enhanced_animals