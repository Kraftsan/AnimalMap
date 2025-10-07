import requests
import json
import os
from datetime import datetime, timedelta
from utils.russian_animals_db import RussianAnimalsDB


class TaxonomyTranslator:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        self.translations_cache = os.path.join(cache_dir, "taxonomy_translations.json")
        self.animals_db = RussianAnimalsDB()  # Добавляем базу данных
        os.makedirs(cache_dir, exist_ok=True)
        self._load_translations()

        # Базовый словарь переводов для основных таксонов
        self.base_translations = {
            # Типы (Phylum)
            "Chordata": "Хордовые",
            "Arthropoda": "Членистоногие",
            "Mollusca": "Моллюски",
            "Annelida": "Кольчатые черви",
            "Cnidaria": "Стрекающие",
            "Echinodermata": "Иглокожие",

            # Классы (Class)
            "Mammalia": "Млекопитающие",
            "Aves": "Птицы",
            "Reptilia": "Пресмыкающиеся",
            "Amphibia": "Земноводные",
            "Actinopterygii": "Костные рыбы",
            "Chondrichthyes": "Хрящевые рыбы",
            "Agnatha": "Бесчелюстные",
            "Insecta": "Насекомые",
            "Arachnida": "Паукообразные",
            "Myriapoda": "Многоножки",
            "Crustacea": "Ракообразные",
            "Gastropoda": "Брюхоногие",
            "Bivalvia": "Двустворчатые",
            "Cephalopoda": "Головоногие",
            "Anthozoa": "Коралловые полипы",
            "Hydrozoa": "Гидроидные",
            "Demospongiae": "Обыкновенные губки",
            "Branchiopoda": "Жаброногие",
            "Crocodylia": "Крокодилы",
            "Squamata": "Чешуйчатые",
            "Testudines": "Черепахи",
            "Amphibia": "Земноводные",
            "Reptilia": "Пресмыкающиеся",
            "Actinopterygii": "Костные рыбы",
            "Chondrichthyes": "Хрящевые рыбы",

            # Уберем дублирование
            "Амфибии": "Земноводные",
            "Рептилии": "Пресмыкающиеся",

            # Отряды (Order) - Птицы
            "Passeriformes": "Воробьинообразные",
            "Falconiformes": "Соколообразные",
            "Strigiformes": "Совообразные",
            "Anseriformes": "Гусеобразные",
            "Galliformes": "Курообразные",
            "Charadriiformes": "Ржанкообразные",
            "Columbiformes": "Голубеобразные",
            "Piciformes": "Дятлообразные",
            "Coraciiformes": "Ракшеобразные",

            # Отряды (Order) - Млекопитающие
            "Carnivora": "Хищные",
            "Rodentia": "Грызуны",
            "Lagomorpha": "Зайцеобразные",
            "Artiodactyla": "Парнокопытные",
            "Chiroptera": "Рукокрылые",
            "Eulipotyphla": "Насекомоядные",

            # Семейства (Family) - примеры
            "Passeridae": "Воробьиные",
            "Paridae": "Синицевые",
            "Corvidae": "Врановые",
            "Accipitridae": "Ястребиные",
            "Falconidae": "Соколиные",
            "Anatidae": "Утиные",
            "Phasianidae": "Фазановые",
            "Scolopacidae": "Бекасовые",
            "Laridae": "Чайковые",
            "Strigidae": "Настоящие совы",
            "Mustelidae": "Куньи",
            "Canidae": "Псовые",
            "Felidae": "Кошачьи",
            "Ursidae": "Медвежьи",
            "Cervidae": "Оленевые",
            "Leporidae": "Заячьи",
            "Sciuridae": "Беличьи",
            "Muridae": "Мышиные",

            # Русские названия животных
            "Vulpes vulpes": "Обыкновенная лисица",
            "Lepus timidus": "Заяц-беляк",
            "Alces alces": "Лось",
            "Capreolus pygargus": "Косуля",
            "Sciurus vulgaris": "Обыкновенная белка",
            "Ursus arctos": "Бурый медведь",
            "Canis lupus": "Волк",
            "Lynx lynx": "Рысь",
            "Martes zibellina": "Соболь",
            "Parus major": "Большая синица",
            "Garrulus glandarius": "Сойка",
            "Pica pica": "Сорока",
            "Dendrocopos major": "Большой пёстрый дятел",
            "Regulus regulus": "Королёк",
            "Strix uralensis": "Длиннохвостая неясыть",
            "Milvus migrans": "Чёрный коршун",
            "Dryocopus martius": "Желна",
            "Bombycilla garrulus": "Свиристель",
            "Hyla arborea": "Обыкновенная квакша",
            "Rana temporaria": "Травяная лягушка",
            "Emberiza pallasi": "Овсянка Палласа",
            "Motacilla alba": "Белая трясогузка",
            "Fringilla coelebs": "Зяблик",
            "Podiceps cristatus": "Большая поганка",
            "Chroicocephalus ridibundus": "Озёрная чайка",
            "Ovis nivicola": "Снежный баран",
            "Rangifer tarandus": "Северный олень",
            "Capreolus pygargus": "Сибирская косуля",
            "Lepus mandshuricus": "Маньчжурский заяц",
            "Urocitellus undulatus": "Длиннохвостый суслик",
            "Mustela sibirica": "Сибирская колонка",
            "Panthera tigris altaica": "Амурский тигр",
            "Eutamias sibiricus": "Азиатский бурундук",
            "Meles leucurus": "Азиатский барсук",
            "Ondatra zibethicus": "Ондатра",
            "Ursus thibetanus ussuricus": "Гималайский медведь",
            "Pteromys volans": "Обыкновенная летяга",
            "Ochotona hyperborea": "Северная пищуха",
            "Myopus schisticolor": "Лесной лемминг",
            "Sorex caecutiens": "Средняя бурозубка",
            "Lynx lynx stroganovi": "Амурская рысь",
            "Alexandromys maximowiczii": "Полёвка Максимовича",
            "Craseomys rufocanus": "Красно-серая полёвка",
            "Clethrionomys rutilus": "Красная полёвка",
            "Apodemus peninsulae": "Корейская мышь",
            "Sorex isodon": "Равнозубая бурозубка",
            "Myodes rutilus": "Красная полёвка",
            "Myodes rufocanus": "Красно-серая полёвка",
            "Tamias sibiricus": "Азиатский бурундук",
            "Alticola lemminus": "Лемминговая полёвка",
            "Microtus mongolicus": "Монгольская полёвка",
            "Microtus maximowiczii": "Полёвка Максимовича",
            "Plecotus ognevi": "Сибирский ушан",
            "Phalacrocorax carbo": "Большой баклан"
        }

    def _load_translations(self):
        """Загружает кэш переводов"""
        try:
            with open(self.translations_cache, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.translations = {}

    def _save_translations(self):
        """Сохраняет кэш переводов"""
        try:
            with open(self.translations_cache, 'w', encoding='utf-8') as f:
                json.dump(self.translations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения переводов: {e}")

    def translate_taxon(self, taxon_name, taxon_rank):
        """Переводит таксон на русский язык"""
        if not taxon_name or taxon_name in ['Не указано', 'Unknown']:
            return 'Не указано'

        # Проверяем базовый словарь
        if taxon_name in self.base_translations:
            return self.base_translations[taxon_name]

        # Проверяем кэш
        cache_key = f"{taxon_rank}_{taxon_name}"
        if cache_key in self.translations:
            cached = self.translations[cache_key]
            # Проверяем не устарел ли кэш (30 дней)
            if datetime.now().timestamp() - cached.get('timestamp', 0) < 30 * 24 * 3600:
                return cached['translation']

        # Ищем перевод через API
        translation = self._translate_via_api(taxon_name, taxon_rank)

        # Сохраняем в кэш
        self.translations[cache_key] = {
            'translation': translation,
            'timestamp': datetime.now().timestamp()
        }
        self._save_translations()

        return translation

    def _translate_via_api(self, taxon_name, taxon_rank):
        """Переводит таксон через API GBIF и другие источники"""
        # Сначала пробуем GBIF API для получения русских названий
        try:
            # Ищем таксон в GBIF
            search_url = f"https://api.gbif.org/v1/species/search"
            params = {
                'q': taxon_name,
                'limit': 1
            }
            response = requests.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    species_key = data['results'][0]['key']

                    # Получаем vernacular names
                    vern_url = f"https://api.gbif.org/v1/species/{species_key}/vernacularNames"
                    vern_response = requests.get(vern_url, timeout=10)
                    if vern_response.status_code == 200:
                        vern_data = vern_response.json()
                        for vern in vern_data.get('results', []):
                            if vern.get('language') == 'rus':
                                return vern.get('vernacularName')
        except:
            pass

        # Если не нашли через GBIF, возвращаем оригинальное название
        return taxon_name

    def translate_animal_data(self, animal_data):
        """Переводит все таксоны в данных о животном с улучшением названий"""
        translated = animal_data.copy()

        # Переводим основные таксоны
        taxon_fields = {
            'phylum': 'phylum',
            'class': 'class',
            'order': 'order',
            'family': 'family',
            'genus': 'genus',
            'species': 'species'
        }

        for field, rank in taxon_fields.items():
            if field in translated and translated[field]:
                translated[f'{field}_ru'] = self.translate_taxon(translated[field], rank)

        # Улучшаем русское название через базу данных
        scientific_name = translated.get('scientific_name')
        if scientific_name and (not translated.get('common_name') or translated.get('common_name') == 'Не указано'):
            common_name = self.animals_db.get_common_name(scientific_name)
            if common_name:
                translated['common_name'] = common_name
                translated['name_source'] = 'local_db'

        return translated