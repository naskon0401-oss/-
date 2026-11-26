import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Set, Tuple
from lxml import etree

# Расширенный словарь овощей, фруктов и ягод для генерации названий энергообъектов
VEGETABLES_AND_FRUITS = [
    "Томат", "Огурец", "Картофель", "Морковь", "Свекла", "Капуста", "Лук", "Чеснок",
    "Перец", "Баклажан", "Кабачок", "Тыква", "Редис", "Редька", "Репа", "Брюква",
    "Сельдерей", "Петрушка", "Укроп", "Шпинат", "Щавель", "Салат", "Брокколи", "Артишок",
    "Спаржа", "Горох", "Фасоль", "Чечевица", "Нут", "Кукуруза", "Патиссон", "Фенхель",
    "Хрен", "Имбирь", "Пастернак", "Топинамбур", "Батат", "Ямс", "Ревень", "Кольраби",
    "Яблоко", "Груша", "Слива", "Вишня", "Черешня", "Абрикос", "Персик", "Нектарин",
    "Алыча", "Айва", "Хурма", "Гранат", "Инжир", "Финик", "Банан", "Ананас",
    "Апельсин", "Мандарин", "Лимон", "Лайм", "Грейпфрут", "Помело", "Кумкват", "Бергамот",
    "Киви", "Манго", "Папайя", "Авокадо", "Гуава", "Личи", "Маракуйя", "Карамбола",
    "Кокос", "Виноград", "Арбуз", "Дыня", "Клубника", "Земляника", "Малина", "Ежевика",
    "Черника", "Голубика", "Брусника", "Клюква", "Смородина", "Крыжовник", "Облепиха", "Рябина",
    "Калина", "Шиповник", "Боярышник", "Ирга", "Шелковица", "Жимолость", "Морошка", "Костяника",
    "Дюриан", "Джекфрут", "Рамбутан", "Мангостин", "Питайя", "Тамаринд", "Фейхоа", "Цитрон",
]

MALE_GIVEN_NAMES = [
    "Александр", "Алексей", "Андрей", "Антон", "Артем", "Борис", "Вадим", "Валентин",
    "Валерий", "Василий", "Виктор", "Виталий", "Владимир", "Владислав", "Вячеслав", "Геннадий",
    "Георгий", "Григорий", "Даниил", "Денис", "Дмитрий", "Евгений", "Егор", "Иван",
    "Игорь", "Илья", "Кирилл", "Константин", "Лев", "Леонид", "Максим", "Михаил",
    "Никита", "Николай", "Олег", "Павел", "Петр", "Роман", "Руслан", "Сергей",
    "Станислав", "Степан", "Тимофей", "Федор", "Юрий", "Ярослав", "Матвей", "Арсений",
]

FEMALE_GIVEN_NAMES = [
    "Александра", "Алина", "Алла", "Анастасия", "Ангелина", "Анна", "Валентина", "Валерия",
    "Варвара", "Вера", "Вероника", "Виктория", "Галина", "Дарья", "Диана", "Евгения",
    "Екатерина", "Елена", "Елизавета", "Жанна", "Зинаида", "Инна", "Ирина", "Кира",
    "Кристина", "Ксения", "Лариса", "Лидия", "Любовь", "Людмила", "Маргарита", "Марина",
    "Мария", "Надежда", "Наталья", "Нина", "Оксана", "Ольга", "Полина", "Светлана",
    "София", "Тамара", "Татьяна", "Ульяна", "Юлия", "Яна", "Олеся", "Таисия",
]

STREET_TYPES = ["ул.", "пр-кт", "пер.", "б-р", "ш.", "проезд"]
LEGAL_FORMS = ["ООО", "АО", "ПАО", "ЗАО", "МУП", "ГУП"]

ENERGY_PREFIX_MAP = {
    "substation": "ПС",
    "transformersubstation": "ТП",
    "line": "ЛЭП",
    "aclinesegment": "ЛЭП",
    "dclinesegment": "ЛЭП",
    "switchgear": "РП",
    "bay": "ЯЧ",
    "breaker": "В",
    "disconnector": "Р",
    "powertransformer": "Т",
    "currenttransformer": "ТТ",
    "potentialtransformer": "ТН",
    "pole": "Опора",
    "busbarsection": "СШ",
    "generatingunit": "ГА",
    "energyconsumer": "Потребитель",
    "controlarea": "РДУ",
    "subgeographicalregion": "ПЭС",
    "geographicalregion": "ОЭС",
}

PRESERVED_GENERIC_NAMES = {
    "Equivalent of Global Objects",
    "Local Objects",
    "Backup",
    "switch device",
    "P LV AT2",
    "Q LV AT2",
    "I LV AT2",
    "U HH AT2",
    "Температурная зависимость",
}

TARGET_TAGS = {
    "Asset.serialNumber",
    "Asset.lotNumber",
    "IdentifiedObject.mRIDStr",
    "IdentifiedObject.name",
    "IdentifiedObject.aliasName",
    "Equipment.nameplate",
    "IPConnectionPoint.address",
    "StreetDetail.name",
    "TownDetail.name",
    "TownDetail.section",
    "TelephoneNumber.localNumber",
    "ElectronicAddress.email",
    "PositionPoint.xPosition",
    "PositionPoint.yPosition",
    "PositionPoint.zPosition",
    "Person.lastName",
    "Person.firstName",
    "Person.mName",
    "Organisation.name",
    "Customer.pucNumber",
    "IdentifiedObject.description",
    "Document.comment",
    "Document.subject",
    "Document.title",
    "ActivityRecord.reason",
    "UsagePoint.serviceDeliveryRemark",
    "StreetDetail.addressGeneral",
}

FREE_TEXT_TAGS = {
    "IdentifiedObject.description",
    "Document.comment",
    "Document.subject",
    "Document.title",
    "ActivityRecord.reason",
    "UsagePoint.serviceDeliveryRemark",
    "StreetDetail.addressGeneral",
}

RE_MRID = re.compile(r"^([A-Za-z0-9_]+?)(\d+)([A-Za-z0-9_.]*)$")
RE_VOLTAGE_ONLY = re.compile(r"^\d+(?:\.\d+)?\s*(?:kV|V|кВ|В)$", flags=re.IGNORECASE)
RE_VOLTAGE_INLINE = re.compile(r"(\d+(?:[.,]\d+)?\s*(?:кВ|kV|В|V))", flags=re.IGNORECASE)
RE_IP = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
RE_LONG_NUM = re.compile(r"\b\d{5,}\b")
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_PHONE = re.compile(r"(\+7|8)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}")
RE_INN = re.compile(r"\b\d{10,12}\b")


class RussianMorphologyEngine:
    """Генерирует прилагательные из названий овощей/фруктов и формы ФИО."""

    EXCEPTIONS = {
        "томат": ("Томатный", "Томатная", "Томатное"),
        "огурец": ("Огуречный", "Огуречная", "Огуречное"),
        "картофель": ("Картофельный", "Картофельная", "Картофельное"),
        "морковь": ("Морковный", "Морковная", "Морковное"),
        "свекла": ("Свекольный", "Свекольная", "Свекольное"),
        "капуста": ("Капустный", "Капустная", "Капустное"),
        "лук": ("Луковый", "Луковая", "Луковое"),
        "чеснок": ("Чесночный", "Чесночная", "Чесночное"),
        "перец": ("Перечный", "Перечная", "Перечное"),
        "баклажан": ("Баклажанный", "Баклажанная", "Баклажанное"),
        "кабачок": ("Кабачковый", "Кабачковая", "Кабачковое"),
        "тыква": ("Тыквенный", "Тыквенная", "Тыквенное"),
        "редис": ("Редисочный", "Редисочная", "Редисочное"),
        "редька": ("Редечный", "Редечная", "Редечное"),
        "репа": ("Репный", "Репная", "Репное"),
        "брюква": ("Брюквенный", "Брюквенная", "Брюквенное"),
        "сельдерей": ("Сельдерейный", "Сельдерейная", "Сельдерейное"),
        "петрушка": ("Петрушечный", "Петрушечная", "Петрушечное"),
        "укроп": ("Укропный", "Укропная", "Укропное"),
        "шпинат": ("Шпинатный", "Шпинатная", "Шпинатное"),
        "щавель": ("Щавелевый", "Щавелевая", "Щавелевое"),
        "салат": ("Салатный", "Салатная", "Салатное"),
        "брокколи": ("Брокколевый", "Брокколевая", "Брокколевое"),
        "артишок": ("Артишоковый", "Артишоковая", "Артишоковое"),
        "спаржа": ("Спаржевый", "Спаржевая", "Спаржевое"),
        "горох": ("Гороховый", "Гороховая", "Гороховое"),
        "фасоль": ("Фасолевый", "Фасолевая", "Фасолевое"),
        "чечевица": ("Чечевичный", "Чечевичная", "Чечевичное"),
        "нут": ("Нутовый", "Нутовая", "Нутовое"),
        "кукуруза": ("Кукурузный", "Кукурузная", "Кукурузное"),
        "патиссон": ("Патиссонный", "Патиссонная", "Патиссонное"),
        "фенхель": ("Фенхелевый", "Фенхелевая", "Фенхелевое"),
        "хрен": ("Хреновый", "Хреновая", "Хреновое"),
        "имбирь": ("Имбирный", "Имбирная", "Имбирное"),
        "пастернак": ("Пастернаковый", "Пастернаковая", "Пастернаковое"),
        "топинамбур": ("Топинамбуровый", "Топинамбуровая", "Топинамбуровое"),
        "батат": ("Бататовый", "Бататовая", "Бататовое"),
        "ямс": ("Ямсовый", "Ямсовая", "Ямсовое"),
        "ревень": ("Ревеневый", "Ревеневая", "Ревеневое"),
        "кольраби": ("Кольрабиевый", "Кольрабиевая", "Кольрабиевое"),
        "яблоко": ("Яблочный", "Яблочная", "Яблочное"),
        "груша": ("Грушевый", "Грушевая", "Грушевое"),
        "слива": ("Сливовый", "Сливовая", "Сливовое"),
        "вишня": ("Вишнёвый", "Вишнёвая", "Вишнёвое"),
        "черешня": ("Черешневый", "Черешневая", "Черешневое"),
        "абрикос": ("Абрикосовый", "Абрикосовая", "Абрикосовое"),
        "персик": ("Персиковый", "Персиковая", "Персиковое"),
        "нектарин": ("Нектариновый", "Нектариновая", "Нектариновое"),
        "алыча": ("Алычовый", "Алычовая", "Алычовое"),
        "айва": ("Айвовый", "Айвовая", "Айвовое"),
        "хурма": ("Хурмовый", "Хурмовая", "Хурмовое"),
        "гранат": ("Гранатовый", "Гранатовая", "Гранатовое"),
        "инжир": ("Инжирный", "Инжирная", "Инжирное"),
        "финик": ("Финиковый", "Финиковая", "Финиковое"),
        "банан": ("Банановый", "Банановая", "Банановое"),
        "ананас": ("Ананасовый", "Ананасовая", "Ананасовое"),
        "апельсин": ("Апельсиновый", "Апельсиновая", "Апельсиновое"),
        "мандарин": ("Мандариновый", "Мандариновая", "Мандариновое"),
        "лимон": ("Лимонный", "Лимонная", "Лимонное"),
        "лайм": ("Лаймовый", "Лаймовая", "Лаймовое"),
        "грейпфрут": ("Грейпфрутовый", "Грейпфрутовая", "Грейпфрутовое"),
        "помело": ("Помеловый", "Помеловая", "Помеловое"),
        "кумкват": ("Кумкватовый", "Кумкватовая", "Кумкватовое"),
        "бергамот": ("Бергамотовый", "Бергамотовая", "Бергамотовое"),
        "киви": ("Кивиевый", "Кивиевая", "Кивиевое"),
        "манго": ("Манговый", "Манговая", "Манговое"),
        "папайя": ("Папайевый", "Папайевая", "Папайевое"),
        "авокадо": ("Авокадовый", "Авокадовая", "Авокадовое"),
        "гуава": ("Гуавовый", "Гуавовая", "Гуавовое"),
        "личи": ("Личиевый", "Личиевая", "Личиевое"),
        "маракуйя": ("Маракуйевый", "Маракуйевая", "Маракуйевое"),
        "карамбола": ("Карамболовый", "Карамболовая", "Карамболовое"),
        "кокос": ("Кокосовый", "Кокосовая", "Кокосовое"),
        "виноград": ("Виноградный", "Виноградная", "Виноградное"),
        "арбуз": ("Арбузный", "Арбузная", "Арбузное"),
        "дыня": ("Дынный", "Дынная", "Дынное"),
        "клубника": ("Клубничный", "Клубничная", "Клубничное"),
        "земляника": ("Земляничный", "Земляничная", "Земляничное"),
        "малина": ("Малиновый", "Малиновая", "Малиновое"),
        "ежевика": ("Ежевичный", "Ежевичная", "Ежевичное"),
        "черника": ("Черничный", "Черничная", "Черничное"),
        "голубика": ("Голубичный", "Голубичная", "Голубичное"),
        "брусника": ("Брусничный", "Брусничная", "Брусничное"),
        "клюква": ("Клюквенный", "Клюквенная", "Клюквенное"),
        "смородина": ("Смородиновый", "Смородиновая", "Смородиновое"),
        "крыжовник": ("Крыжовниковый", "Крыжовниковая", "Крыжовниковое"),
        "облепиха": ("Облепиховый", "Облепиховая", "Облепиховое"),
        "рябина": ("Рябиновый", "Рябиновая", "Рябиновое"),
        "калина": ("Калиновый", "Калиновая", "Калиновое"),
        "шиповник": ("Шиповниковый", "Шиповниковая", "Шиповниковое"),
        "боярышник": ("Боярышниковый", "Боярышниковая", "Боярышниковое"),
        "ирга": ("Ирговый", "Ирговая", "Ирговое"),
        "шелковица": ("Шелковичный", "Шелковичная", "Шелковичное"),
        "жимолость": ("Жимолостный", "Жимолостная", "Жимолостное"),
        "морошка": ("Морошковый", "Морошковая", "Морошковое"),
        "костяника": ("Костяничный", "Костяничная", "Костяничное"),
        "дюриан": ("Дюриановый", "Дюриановая", "Дюриановое"),
        "джекфрут": ("Джекфрутовый", "Джекфрутовая", "Джекфрутовое"),
        "рамбутан": ("Рамбутановый", "Рамбутановая", "Рамбутановое"),
        "мангостин": ("Мангостиновый", "Мангостиновая", "Мангостиновое"),
        "питайя": ("Питайевый", "Питайевая", "Питайевое"),
        "тамаринд": ("Тамариндовый", "Тамариндовая", "Тамариндовое"),
        "фейхоа": ("Фейхоавый", "Фейхоавая", "Фейхоавое"),
        "цитрон": ("Цитроновый", "Цитроновая", "Цитроновое"),
    }

    TRANSLIT_MAP = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }

    @classmethod
    def produce_to_adjective(cls, noun: str, gender: str = "m") -> str:
        key = noun.strip().lower()
        if key in cls.EXCEPTIONS:
            forms = cls.EXCEPTIONS[key]
            return {"m": forms[0], "f": forms[1], "n": forms[2]}.get(gender, forms[0])
        stem = key[:-1] if key.endswith(("а", "я", "о", "е", "ь", "й")) else key
        base = stem.capitalize() + "ов"
        if gender == "f":
            return base + "ая"
        if gender == "n":
            return base + "ое"
        return base + "ый"

    @classmethod
    def name_to_person_forms(cls, given_name: str, is_female: bool = False) -> Tuple[str, str, str, str]:
        clean = given_name.strip()
        low = clean.lower()
        if low.endswith(("й", "ь")):
            stem = clean[:-1]
            return (
                stem + ("ева" if is_female else "ев"),
                clean,
                stem + ("евна" if is_female else "евич"),
                stem + "евская",
            )
        if low.endswith(("а", "я")):
            stem = clean[:-1]
            patr_suf = ("инична" if is_female else "ич") if low.endswith("я") else ("ична" if is_female else "ич")
            return (
                stem + ("ина" if is_female else "ин"),
                clean,
                stem + patr_suf,
                stem + "инская",
            )
        return (
            clean + ("ова" if is_female else "ов"),
            clean,
            clean + ("овна" if is_female else "ович"),
            clean + "овская",
        )

    @classmethod
    def transliterate(cls, text: str) -> str:
        return "".join(
            cls.TRANSLIT_MAP[ch] if ch in cls.TRANSLIT_MAP else (ch if ch.isalnum() else "")
            for ch in text.lower()
        )


@dataclass
class AnonymizationStats:
    elements_processed: int = 0
    names_anonymized: int = 0
    mrids_anonymized: int = 0
    serials_anonymized: int = 0
    persons_anonymized: int = 0
    orgs_anonymized: int = 0
    addresses_anonymized: int = 0
    ips_anonymized: int = 0
    coords_anonymized: int = 0
    free_texts_masked: int = 0
    class_counts: Dict[str, int] = field(default_factory=dict)


class FastCIMAnonymizer:
    """Быстрый детерминированный генератор псевдонимов с кэшированием по словарю."""

    def __init__(self, salt: str = "cim16-anonymizer-2026"):
        self.salt = salt.encode("utf-8")
        self.mapping: Dict[Tuple[str, str], str] = {}
        self.person_cache: Dict[str, Dict[str, str]] = {}
        self.used_by_category: Dict[str, Set[str]] = {}
        self.secret_replacements: List[Tuple[str, str]] = []
        self._seen_secrets: Set[str] = set()
        self.stats = AnonymizationStats()

    def _seed(self, category: str, value: str, attempt: int = 0) -> int:
        digest = hashlib.blake2b(
            f"{category}::{value}::{attempt}".encode("utf-8"),
            digest_size=16,
            key=self.salt,
        ).digest()
        return int.from_bytes(digest, "little")

    def _unique(self, category: str, original: str, builder: Callable[[int], str]) -> str:
        clean = original.strip()
        if not clean:
            return original
        key = (category, clean)
        cached = self.mapping.get(key)
        if cached is not None:
            return cached

        used = self.used_by_category.setdefault(category, set())
        attempt = 0
        while True:
            seed = self._seed(category, clean, attempt)
            cand = builder(seed)
            if cand not in used:
                used.add(cand)
                self.mapping[key] = cand
                if len(clean) >= 5 and not clean.isdigit() and clean not in self._seen_secrets:
                    self._seen_secrets.add(clean)
                    self.secret_replacements.append((clean, cand))
                return cand
            attempt += 1

    def generate_digits(self, category: str, original: str) -> str:
        digits_only = "".join(ch for ch in original if ch.isdigit())
        length = len(digits_only)
        if length == 0:
            return original

        def _build(seed: int) -> str:
            cur = seed
            out = []
            for idx in range(length):
                cur = (cur * 6364136223846793005 + 1442695040888963407 + idx) & ((1 << 64) - 1)
                d = cur % 10
                if idx == 0 and length > 1 and d == 0:
                    d = 1
                out.append(str(d))
            return "".join(out)

        return self._unique(category, original, _build)

    def get_person_identity(self, person_key: str) -> Dict[str, str]:
        cached = self.person_cache.get(person_key)
        if cached is not None:
            return cached

        seed0 = self._seed("person_identity", person_key, 0)
        is_female = bool(seed0 & 1)
        pool = FEMALE_GIVEN_NAMES if is_female else MALE_GIVEN_NAMES
        used_fios = self.used_by_category.setdefault("person_fio", set())
        attempt = 0

        while True:
            s = self._seed("person_identity", person_key, attempt)
            base_name = pool[s % len(pool)]
            patr_src = MALE_GIVEN_NAMES[(s >> 8) % len(MALE_GIVEN_NAMES)]
            surname, first_name, _, street_root = RussianMorphologyEngine.name_to_person_forms(
                base_name, is_female=is_female
            )
            _, _, patronymic, _ = RussianMorphologyEngine.name_to_person_forms(
                patr_src, is_female=is_female
            )
            fio = f"{surname} {first_name} {patronymic}"
            if fio not in used_fios:
                used_fios.add(fio)
                street_type = STREET_TYPES[(s >> 16) % len(STREET_TYPES)]
                house_num = ((s >> 24) % 240) + 1
                login = RussianMorphologyEngine.transliterate(f"{surname}.{first_name}")
                email_num = ((s >> 32) % 900) + 100
                p_code = 900 + ((s >> 40) % 99)
                p_a = 100 + ((s >> 48) % 899)
                p_b = (s >> 56) % 100
                p_c = (s >> 64) % 100
                ident = {
                    "lastName": surname,
                    "firstName": first_name,
                    "mName": patronymic,
                    "fio": fio,
                    "email": f"{login}{email_num}@grid-model.local",
                    "street": f"{street_type} {street_root}",
                    "house": str(house_num),
                    "phone": f"+7 ({p_code:03d}) {p_a:03d}-{p_b:02d}-{p_c:02d}",
                }
                self.person_cache[person_key] = ident
                clean_key = person_key.strip()
                if len(clean_key) >= 5 and not clean_key.isdigit() and clean_key not in self._seen_secrets:
                    self._seen_secrets.add(clean_key)
                    self.secret_replacements.append((clean_key, fio))
                return ident
            attempt += 1

    def generate_produce_phrase(self, category: str, original: str, gender: str = "m") -> str:
        def _build(seed: int) -> str:
            idx_a = seed % len(VEGETABLES_AND_FRUITS)
            idx_b = (seed // len(VEGETABLES_AND_FRUITS)) % len(VEGETABLES_AND_FRUITS)
            num = ((seed >> 20) % 999) + 1
            adj_a = RussianMorphologyEngine.produce_to_adjective(VEGETABLES_AND_FRUITS[idx_a], gender=gender)
            if idx_a == idx_b:
                return f"{adj_a}-{num:03d}"
            adj_b = RussianMorphologyEngine.produce_to_adjective(VEGETABLES_AND_FRUITS[idx_b], gender=gender)
            return f"{adj_a}-{adj_b}-{num:03d}"

        return self._unique(category, original, _build)

    def generate_org_name(self, original: str) -> str:
        def _build(seed: int) -> str:
            form = LEGAL_FORMS[seed % len(LEGAL_FORMS)]
            idx = (seed >> 8) % len(VEGETABLES_AND_FRUITS)
            num = ((seed >> 20) % 999) + 1
            adj = RussianMorphologyEngine.produce_to_adjective(VEGETABLES_AND_FRUITS[idx], gender="n")
            return f"{form} «{adj} Энерго-{num:03d}»"

        return self._unique("org_name", original, _build)

    def generate_energy_object_name(self, cim_class: str, original: str) -> str:
        clean = original.strip()
        if not clean or clean in PRESERVED_GENERIC_NAMES:
            return original
        if RE_VOLTAGE_ONLY.fullmatch(clean):
            return original
        if clean.isdigit():
            return self.generate_digits(f"obj_num:{cim_class}", clean)

        prefix = ENERGY_PREFIX_MAP.get(cim_class.lower())
        if prefix is None:
            upper_clean = clean.upper()
            for cand in ("ПС", "ТП", "ЛЭП", "РП", "КТП", "БКТП", "ОРУ", "ЗРУ", "ВЛ", "КЛ"):
                if upper_clean.startswith(cand + "-") or upper_clean.startswith(cand + " "):
                    prefix = cand
                    break
        if prefix is None:
            prefix = "ОБЪЕКТ"

        v_match = RE_VOLTAGE_INLINE.search(clean)
        voltage_tail = f" {v_match.group(1)}" if v_match else ""

        def _build(seed: int) -> str:
            idx = seed % len(VEGETABLES_AND_FRUITS)
            num = ((seed >> 16) % 9999) + 1
            gender = "f" if prefix in {"ПС", "ТП", "ЛЭП", "ВЛ", "КЛ", "Опора", "ЯЧ"} else "m"
            adj = RussianMorphologyEngine.produce_to_adjective(VEGETABLES_AND_FRUITS[idx], gender=gender)
            return f"{prefix}-{num:04d} «{adj}»{voltage_tail}"

        return self._unique(f"energy_obj:{prefix}", clean, _build)

    def anonymize_mrid_str(self, original: str) -> str:
        clean = original.strip()
        m = RE_MRID.match(clean)
        if not m:
            return original
        prefix, digits, suffix = m.groups()
        return f"{prefix}{self.generate_digits(f'mrid:{prefix}', digits)}{suffix}"

    def anonymize_ip_address(self, original: str) -> str:
        clean = original.strip()
        if not RE_IP.fullmatch(clean):
            return original

        def _build(seed: int) -> str:
            b2 = (seed >> 8) % 254 + 1
            b3 = (seed >> 16) % 254 + 1
            b4 = (seed >> 24) % 254 + 1
            return f"10.{b2}.{b3}.{b4}"

        return self._unique("ip_address", clean, _build)

    def anonymize_coordinate(self, axis: str, original: str) -> str:
        clean = original.strip()
        try:
            val = float(clean.replace(",", "."))
        except ValueError:
            return original
        seed = self._seed(f"coord:{axis}", clean, 0)
        shift = ((seed % 200000) - 100000) / 100000.0
        decimals = len(clean.split(".")[1]) if "." in clean else 6
        return f"{val + shift:.{decimals}f}"

    def mask_free_text(self, text: str) -> str:
        if not text:
            return text
        masked = text
        if self.secret_replacements:
            for orig, syn in self.secret_replacements:
                if orig in masked:
                    masked = masked.replace(orig, syn)
        if "@" in masked:
            masked = RE_EMAIL.sub("masked@grid-model.local", masked)
        masked = RE_PHONE.sub("+7 (900) 000-00-00", masked)
        masked = RE_INN.sub(lambda m: self.generate_digits("free_inn", m.group(0)), masked)
        return masked


def local_name(tag: str) -> str:
    idx = tag.rfind("}")
    return tag[idx + 1 :] if idx != -1 else tag


class FastCIMStreamProcessor:
    """Однопроходный потоковый процессор CIM16/RDF XML без лишних событий и временных файлов."""

    def __init__(self, anonymizer: FastCIMAnonymizer, shift_coordinates: bool = True):
        self.anon = anonymizer
        self.shift_coordinates = shift_coordinates

    def process_element(self, elem: etree._Element) -> None:
        cim_class = local_name(elem.tag)
        self.anon.stats.elements_processed += 1
        self.anon.stats.class_counts[cim_class] = self.anon.stats.class_counts.get(cim_class, 0) + 1

        if cim_class in {"Person", "Customer", "CrewMember", "Operator", "FieldOperator"}:
            self._process_person(elem)
            return

        if cim_class in {"Organisation", "CustomerAccount", "ServiceSupplier"}:
            self._process_org(elem)
            return

        for node in elem.iter():
            txt = node.text
            if not txt:
                continue
            t = local_name(node.tag)
            if t not in TARGET_TAGS or not txt.strip():
                continue

            if t in {"Asset.serialNumber", "Asset.lotNumber"}:
                node.text = self.anon.generate_digits(t, txt)
                self.anon.stats.serials_anonymized += 1
            elif t == "IdentifiedObject.mRIDStr":
                node.text = self.anon.anonymize_mrid_str(txt)
                self.anon.stats.mrids_anonymized += 1
            elif t == "IdentifiedObject.name":
                new_val = self.anon.generate_energy_object_name(cim_class, txt)
                if new_val != txt:
                    node.text = new_val
                    self.anon.stats.names_anonymized += 1
            elif t == "IdentifiedObject.aliasName":
                node.text = self.anon.generate_produce_phrase(f"alias:{cim_class}", txt)
                self.anon.stats.names_anonymized += 1
            elif t == "Equipment.nameplate":
                node.text = RE_LONG_NUM.sub(lambda m: self.anon.generate_digits("nameplate_serial", m.group(0)), txt)
            elif t == "IPConnectionPoint.address":
                node.text = self.anon.anonymize_ip_address(txt)
                self.anon.stats.ips_anonymized += 1
            elif t in {"StreetDetail.name", "TownDetail.name", "TownDetail.section"}:
                hint = elem.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about") or txt
                node.text = self.anon.get_person_identity(hint)["street"]
                self.anon.stats.addresses_anonymized += 1
            elif t == "TelephoneNumber.localNumber":
                node.text = self.anon.generate_digits("phone_local", txt)
                self.anon.stats.persons_anonymized += 1
            elif t == "ElectronicAddress.email":
                node.text = self.anon.get_person_identity(txt)["email"]
                self.anon.stats.persons_anonymized += 1
            elif self.shift_coordinates and t in {
                "PositionPoint.xPosition",
                "PositionPoint.yPosition",
                "PositionPoint.zPosition",
            }:
                node.text = self.anon.anonymize_coordinate(t, txt)
                self.anon.stats.coords_anonymized += 1
            elif t in FREE_TEXT_TAGS:
                node.text = self.anon.mask_free_text(txt)
                self.anon.stats.free_texts_masked += 1

    def _process_person(self, elem: etree._Element) -> None:
        rdf_about = elem.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about") or ""
        parts = []
        for node in elem.iter():
            if node.text and local_name(node.tag) in {"Person.lastName", "Person.firstName", "Person.mName", "IdentifiedObject.name"}:
                parts.append(node.text.strip())
        person_key = "|".join(parts) if parts else rdf_about
        ident = self.anon.get_person_identity(person_key)
        self.anon.stats.persons_anonymized += 1

        for node in elem.iter():
            txt = node.text
            if not txt or not txt.strip():
                continue
            t = local_name(node.tag)
            if t == "Person.lastName":
                node.text = ident["lastName"]
            elif t == "Person.firstName":
                node.text = ident["firstName"]
            elif t == "Person.mName":
                node.text = ident["mName"]
            elif t == "IdentifiedObject.name":
                node.text = ident["fio"]
            elif t == "IdentifiedObject.mRIDStr":
                node.text = self.anon.anonymize_mrid_str(txt)
            elif t in {"Customer.pucNumber", "Asset.serialNumber"}:
                node.text = self.anon.generate_digits(t, txt)
            elif t in FREE_TEXT_TAGS:
                node.text = self.anon.mask_free_text(txt)

    def _process_org(self, elem: etree._Element) -> None:
        self.anon.stats.orgs_anonymized += 1
        for node in elem.iter():
            txt = node.text
            if not txt or not txt.strip():
                continue
            t = local_name(node.tag)
            if t in {"Organisation.name", "IdentifiedObject.name"}:
                node.text = self.anon.generate_org_name(txt)
            elif t == "IdentifiedObject.mRIDStr":
                node.text = self.anon.anonymize_mrid_str(txt)
            elif t in FREE_TEXT_TAGS:
                node.text = self.anon.mask_free_text(txt)

    def run_stream(self, input_path: Path, output_path: Path, report_path: Optional[Path] = None) -> None:
        start_ts = time.time()
        context = etree.iterparse(str(input_path), events=("end",), huge_tree=True)

        root = None
        ns_header = ""
        root_qname = "rdf:RDF"
        header_written = False
        processed = 0

        with open(output_path, "wb") as out_f:
            for _, elem in context:
                parent = elem.getparent()
                if parent is None:
                    root = elem
                    break

                if not header_written:
                    root = parent
                    ns_parts = [
                        f'xmlns="{uri}"' if prefix is None else f'xmlns:{prefix}="{uri}"'
                        for prefix, uri in (root.nsmap or {}).items()
                    ]
                    ns_header = (" " + " ".join(ns_parts)) if ns_parts else ""
                    root_qname = self._qname_with_prefix(root)
                    out_f.write(b'<?xml version="1.0" encoding="utf-8"?>\\n')
                    out_f.write(f"<{root_qname}{ns_header}>\\n".encode("utf-8"))
                    header_written = True

                self.process_element(elem)
                out_f.write(b"  ")
                out_f.write(etree.tostring(elem, encoding="utf-8"))
                out_f.write(b"\\n")

                elem.clear()
                while elem.getprevious() is not None:
                    del parent[0]

                processed += 1
                if processed % 100000 == 0:
                    elapsed = time.time() - start_ts
                    print(f"[Обработка] Элементов: {processed} | Прошло: {elapsed:.1f} сек", flush=True)

            if not header_written and root is not None:
                ns_parts = [
                    f'xmlns="{uri}"' if prefix is None else f'xmlns:{prefix}="{uri}"'
                    for prefix, uri in (root.nsmap or {}).items()
                ]
                ns_header = (" " + " ".join(ns_parts)) if ns_parts else ""
                root_qname = self._qname_with_prefix(root)
                out_f.write(b'<?xml version="1.0" encoding="utf-8"?>\\n')
                out_f.write(f"<{root_qname}{ns_header}>\\n".encode("utf-8"))

            out_f.write(f"</{root_qname}>\\n".encode("utf-8"))

        del context
        elapsed = time.time() - start_ts

        if report_path:
            summary = {
                "input_file": str(input_path.resolve()),
                "output_file": str(output_path.resolve()),
                "elapsed_seconds": round(elapsed, 2),
                "elements_processed": self.anon.stats.elements_processed,
                "names_anonymized": self.anon.stats.names_anonymized,
                "mrids_anonymized": self.anon.stats.mrids_anonymized,
                "serials_anonymized": self.anon.stats.serials_anonymized,
                "persons_anonymized": self.anon.stats.persons_anonymized,
                "orgs_anonymized": self.anon.stats.orgs_anonymized,
                "addresses_anonymized": self.anon.stats.addresses_anonymized,
                "ips_anonymized": self.anon.stats.ips_anonymized,
                "coords_anonymized": self.anon.stats.coords_anonymized,
                "free_texts_masked": self.anon.stats.free_texts_masked,
                "top_cim_classes": dict(
                    sorted(self.anon.stats.class_counts.items(), key=lambda x: x[1], reverse=True)[:30]
                ),
            }
            report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _qname_with_prefix(elem: etree._Element) -> str:
        tag = elem.tag
        if not tag.startswith("{"):
            return tag
        uri, local = tag[1:].split("}", 1)
        for prefix, ns_uri in (elem.nsmap or {}).items():
            if ns_uri == uri:
                return f"{prefix}:{local}" if prefix else local
        return local


def resolve_input_file(cli_path: Optional[str] = None) -> Path:
    if cli_path:
        candidate = Path(cli_path).expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"Файл не найден: {candidate}")

    env_path = os.environ.get("CIM_INPUT_FILE")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.is_file():
            return candidate

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Выберите исходный файл CIM-модели (XML)",
            filetypes=[("XML и текстовые файлы", "*.xml *.txt *.*"), ("Все файлы", "*.*")],
        )
        root.destroy()
        if selected:
            return Path(selected).resolve()
    except Exception:
        pass

    manual = input("Введите полный путь к исходному файлу модели: ").strip().strip('"')
    candidate = Path(manual).expanduser().resolve()
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Не удалось найти файл по пути: {candidate}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Быстрое потоковое обезличивание CIM16/RDF XML")
    parser.add_argument("-i", "--input", help="Путь к исходному файлу модели")
    parser.add_argument("-o", "--output", help="Путь для сохранения обезличенного файла")
    parser.add_argument("-s", "--salt", default="cim16-production-salt-2026", help="Секретная соль псевдонимизации")
    parser.add_argument("--no-coords", action="store_true", help="Не изменять координаты PositionPoint")
    args = parser.parse_args()

    input_path = resolve_input_file(args.input)
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(f"{input_path.stem}_anonymized.xml")
    )
    report_path = output_path.with_name(f"{output_path.stem}_report.json")

    print(f"Входной файл:  {input_path}", flush=True)
    print(f"Выходной файл: {output_path}", flush=True)

    anonymizer = FastCIMAnonymizer(salt=args.salt)
    processor = FastCIMStreamProcessor(anonymizer=anonymizer, shift_coordinates=not args.no_coords)
    processor.run_stream(input_path=input_path, output_path=output_path, report_path=report_path)

    print("Обезличивание успешно завершено.", flush=True)
    print(f"Итоговый файл модели: {output_path}", flush=True)
    print(f"Статистика обработки: {report_path}", flush=True)


if __name__ == "__main__":
    main()