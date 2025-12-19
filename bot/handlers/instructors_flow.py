from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import DEFAULT_LANGUAGE
from i18n import t
from keyboards.common import main_menu, back_keyboard, choices_keyboard, phone_keyboard, confirm_keyboard
from services.api import ApiClient, ApiClientError, ApiServerError, ApiTimeoutError, ApiNetworkError
from services.analytics import send_event
from states_instructor import InstructorFlow
from utils.validators import normalize_phone
from utils.whatsapp import build_wa_link_instructor

router = Router()


async def get_language(state: FSMContext) -> str:
    """Получить язык из state или вернуть дефолтный"""
    data = await state.get_data()
    return data.get("language", DEFAULT_LANGUAGE)


def is_back(text: str, lang: str = "RU") -> bool:
    """Проверить, является ли текст командой 'Назад'"""
    if not text:
        return False
    text_lower = text.lower()
    if lang == "KZ":
        return text_lower in {"артқа", "назад"}
    return text_lower in {"назад"}


def is_main_menu(text: str, lang: str = "RU") -> bool:
    """Проверить, является ли текст командой 'Главное меню'"""
    if not text:
        return False
    text_lower = text.lower()
    if lang == "KZ":
        return text_lower in {"басты мәзір", "главное меню"}
    return text_lower in {"главное меню"}


def get_name_by_lang(item: dict, lang: str) -> str:
    """Получить название на нужном языке"""
    if lang == "KZ" and "name_kz" in item:
        return item.get("name_kz") or item.get("name_ru", "")
    return item.get("name_ru", item.get("name", {}).get("ru", ""))


async def handle_api_error(error: Exception, lang: str, message: Message, state: FSMContext):
    """Обработать ошибку API и отправить понятное сообщение пользователю"""
    if isinstance(error, ApiClientError):
        error_msg = t("error_client", lang)
    elif isinstance(error, ApiServerError):
        error_msg = t("error_server", lang)
    elif isinstance(error, ApiTimeoutError):
        error_msg = t("error_timeout", lang)
    elif isinstance(error, ApiNetworkError):
        error_msg = t("error_network", lang)
    else:
        error_msg = t("error_unknown", lang)
    
    await message.answer(error_msg, reply_markup=main_menu(lang))
    await state.clear()


# Обработчики кнопок меню должны быть первыми и работать в любом состоянии
@router.message(F.text.in_(["Главное меню", "Басты мәзір", "главное меню", "басты мәзір"]))
async def handle_main_menu(message: Message, state: FSMContext):
    lang = await get_language(state)
    await state.clear()
    await message.answer(t("main_welcome", lang), reply_markup=main_menu(lang))


@router.message(Command("instructors"))
@router.message(F.text.in_(["Инструкторы", "Нұсқаушылар", "инструкторы"]))
async def instructors_start(message: Message, state: FSMContext):
    # Очищаем текущее состояние перед началом нового потока
    await state.clear()
    lang = await get_language(state)
    await send_event("flow_selected", {"flow": "instructors"}, bot_user_id=message.from_user.id)
    api = ApiClient()
    try:
        cities = await api.get_cities()
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    if not cities:
        await message.answer(t("no_cities", lang), reply_markup=main_menu(lang))
        return
    await state.set_state(InstructorFlow.city)
    await state.update_data(cities=cities, language=lang)
    opts = [f"{c['id']}: {get_name_by_lang(c, lang)}" for c in cities]
    await message.answer(t("choose_city", lang), reply_markup=choices_keyboard(opts, lang))


@router.message(InstructorFlow.city)
async def instructors_choose_city(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # На первом шаге "Назад" ведет в главное меню
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    data = await state.get_data()
    cities = data.get("cities", [])
    city_id = None
    for c in cities:
        if message.text.startswith(f"{c['id']}:"):
            city_id = c["id"]
            break
    if not city_id:
        await message.answer(t("choose_city", lang), reply_markup=choices_keyboard([f"{c['id']}: {get_name_by_lang(c, lang)}" for c in cities], lang))
        return
    await send_event("city_selected", {"city_id": city_id}, bot_user_id=message.from_user.id)
    await state.update_data(city_id=city_id)
    
    # После города - выбор категории согласно новому ТЗ
    api = ApiClient()
    try:
        categories = await api.get_categories()
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    # Фильтрация категорий: только B для потоков без CERT_NOT_PASSED intent
    data = await state.get_data()
    main_intent = data.get("main_intent")
    if main_intent != "CERT_NOT_PASSED":
        # Оставляем только категорию B
        categories = [c for c in categories if c.get('code') == 'B']
        if not categories:
            await message.answer("Категория B не найдена" if lang == "RU" else "B санаты табылмады", reply_markup=main_menu(lang))
            await state.clear()
            return
    
    await state.update_data(categories=categories)
    opts = [f"{c['id']}: {get_name_by_lang(c, lang)}" for c in categories]
    await state.set_state(InstructorFlow.category)
    await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))


@router.message(InstructorFlow.category)
async def instructors_choose_category(message: Message, state: FSMContext):
    """Обработка выбора категории для инструкторов"""
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору города
        data = await state.get_data()
        cities = data.get("cities", [])
        if cities:
            await state.set_state(InstructorFlow.city)
            opts = [f"{c['id']}: {get_name_by_lang(c, lang)}" for c in cities]
            await message.answer(t("choose_city", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    data = await state.get_data()
    categories = data.get("categories", [])
    category_id = None
    category_name = ""
    selected_category = None
    for c in categories:
        if message.text.startswith(f"{c['id']}:"):
            category_id = c["id"]
            category_name = get_name_by_lang(c, lang)
            selected_category = c
            break
    if not category_id:
        await message.answer(t("choose_category", lang), reply_markup=choices_keyboard([f"{c['id']}: {get_name_by_lang(c, lang)}" for c in categories], lang))
        return
    
    # Валидация: проверяем, что выбрана категория B для потоков без CERT_NOT_PASSED
    main_intent = data.get("main_intent")
    if main_intent != "CERT_NOT_PASSED" and selected_category.get('code') != 'B':
        await message.answer(
            "Доступна только категория B" if lang == "RU" else "Тек B санаты қолжетімді",
            reply_markup=choices_keyboard([f"{c['id']}: {get_name_by_lang(c, lang)}" for c in categories], lang)
        )
        return
    
    await send_event("category_selected", {"category_id": category_id}, bot_user_id=message.from_user.id)
    await state.update_data(category_id=category_id, category_name=category_name)
    
    # После категории - выбор КПП
    await state.set_state(InstructorFlow.gearbox)
    gearbox_options = [
        t("gearbox_automatic", lang),
        t("gearbox_manual", lang)
    ]
    await message.answer(t("gearbox_prompt", lang), reply_markup=choices_keyboard(gearbox_options, lang))


@router.message(InstructorFlow.gearbox)
async def instructors_choose_gearbox(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору категории
        data = await state.get_data()
        categories = data.get("categories", [])
        if categories:
            await state.set_state(InstructorFlow.category)
            opts = [f"{c['id']}: {get_name_by_lang(c, lang)}" for c in categories]
            await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Определяем gearbox по тексту кнопки
    gearbox = None
    text_lower = message.text.lower() if message.text else ""
    
    # Проверяем по тексту кнопок (с учетом эмодзи)
    gearbox_auto_ru = t("gearbox_automatic", "RU").lower()
    gearbox_auto_kz = t("gearbox_automatic", "KZ").lower()
    gearbox_manual_ru = t("gearbox_manual", "RU").lower()
    gearbox_manual_kz = t("gearbox_manual", "KZ").lower()
    
    if "автомат" in text_lower or gearbox_auto_ru in text_lower or gearbox_auto_kz in text_lower or "at" in text_lower:
        gearbox = "AT"
    elif "механик" in text_lower or gearbox_manual_ru in text_lower or gearbox_manual_kz in text_lower or "mt" in text_lower:
        gearbox = "MT"
    else:
        # Fallback на старый формат
        gearbox = message.text.strip().upper() if message.text else ""
        if gearbox not in {"AT", "MT"}:
            gearbox_options_ru = [t("gearbox_automatic", lang), t("gearbox_manual", lang)]
            gearbox_options_kz = [t("gearbox_automatic", "KZ"), t("gearbox_manual", "KZ")]
            gearbox_options = gearbox_options_kz if lang == "KZ" else gearbox_options_ru
            await message.answer(t("gearbox_prompt", lang), reply_markup=choices_keyboard(gearbox_options, lang))
            return
    
    await send_event("gearbox_selected", {"gearbox": gearbox}, bot_user_id=message.from_user.id)
    await state.update_data(gearbox=gearbox)
    await state.set_state(InstructorFlow.instructor_gender)
    # Кнопки выбора пола согласно ТЗ
    gender_options = [
        t("gender_male", lang),
        t("gender_female", lang),
        t("gender_any", lang)
    ]
    await message.answer(t("gender_prompt", lang), reply_markup=choices_keyboard(gender_options, lang))




@router.message(InstructorFlow.instructor_gender)
async def instructors_gender(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору КПП
        await state.set_state(InstructorFlow.gearbox)
        gearbox_options = [
            t("gearbox_automatic", lang),
            t("gearbox_manual", lang)
        ]
        await message.answer(t("gearbox_prompt", lang), reply_markup=choices_keyboard(gearbox_options, lang))
        return
    
    # Определяем gender по тексту кнопки
    gender = None
    text = message.text or ""
    text_lower = text.lower()
    
    # Получаем тексты кнопок для сравнения
    gender_male_ru = t("gender_male", "RU").lower()
    gender_male_kz = t("gender_male", "KZ").lower()
    gender_female_ru = t("gender_female", "RU").lower()
    gender_female_kz = t("gender_female", "KZ").lower()
    gender_any_ru = t("gender_any", "RU").lower()
    gender_any_kz = t("gender_any", "KZ").lower()
    
    # Проверяем по тексту кнопок и ключевым словам
    if ("мужчин" in text_lower or "еркек" in text_lower or "👨" in text or 
        gender_male_ru in text_lower or gender_male_kz in text_lower or
        text_lower == "m"):
        gender = "M"
    elif ("женщин" in text_lower or "әйел" in text_lower or "👩" in text or 
          gender_female_ru in text_lower or gender_female_kz in text_lower or
          text_lower == "f"):
        gender = "F"
    elif ("не имеет" in text_lower or "маңызды емес" in text_lower or "⚖" in text or
          gender_any_ru in text_lower or gender_any_kz in text_lower):
        gender = None  # Не имеет значения
    else:
        # Fallback - если не распознали, показываем снова
        gender_options = [
            t("gender_male", lang),
            t("gender_female", lang),
            t("gender_any", lang)
        ]
        await message.answer(t("gender_prompt", lang), reply_markup=choices_keyboard(gender_options, lang))
        return
    
    data = await state.get_data()
    city_id = data.get("city_id")
    gearbox = data.get("gearbox")
    
    if not city_id or not gearbox:
        await message.answer(t("error_unknown", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    
    data = await state.get_data()
    category_id = data.get("category_id")
    if not category_id:
        await message.answer(t("error_unknown", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    
    api = ApiClient()
    try:
        # Если gender=None, не передаем параметр gender в API
        if gender:
            instructors = await api.get_instructors(city_id=city_id, category_id=category_id, gearbox=gearbox, gender=gender)
        else:
            instructors = await api.get_instructors(city_id=city_id, category_id=category_id, gearbox=gearbox)
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    if not instructors or not isinstance(instructors, list):
        await message.answer(t("no_instructors", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    
    await send_event("instructor_gender_selected", {"gender": gender or "ANY"}, bot_user_id=message.from_user.id)
    await state.update_data(instructor_gender=gender, instructors=instructors)
    
    # Формируем список инструкторов для отображения БЕЗ цен согласно новому ТЗ
    opts = []
    for i in instructors:
        instructor_id = i.get('id')
        display_name = i.get('display_name', '')
        if instructor_id and display_name:
            opts.append(f"{instructor_id}: {display_name}")
    
    if not opts:
        await message.answer(t("no_instructors", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    
    await state.set_state(InstructorFlow.instructor)
    await message.answer(t("choose_instructor", lang), reply_markup=choices_keyboard(opts, lang))


@router.message(InstructorFlow.instructor)
async def instructors_choose(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору пола инструктора
        data = await state.get_data()
        instructors = data.get("instructors", [])
        if instructors:
            await state.set_state(InstructorFlow.instructor_gender)
            gender_options = [
                t("gender_male", lang),
                t("gender_female", lang),
                t("gender_any", lang)
            ]
            await message.answer(t("gender_prompt", lang), reply_markup=choices_keyboard(gender_options, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    data = await state.get_data()
    instructors = data.get("instructors", [])
    instructor = None
    for i in instructors:
        if message.text.startswith(f"{i['id']}:"):
            instructor = i
            break
    if not instructor:
        await message.answer(t("choose_instructor", lang), reply_markup=choices_keyboard([f"{i['id']}: {i['display_name']}" for i in instructors], lang))
        return
    await send_event("instructor_opened", {"instructor_id": instructor['id']}, bot_user_id=message.from_user.id)
    
    # Получаем детальную информацию об инструкторе с тарифами
    api = ApiClient()
    try:
        instructor_detail = await api.get_instructor_detail(instructor['id'])
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    # Показываем карточку инструктора БЕЗ цен согласно новому ТЗ
    bio = instructor_detail.get('bio', {})
    bio_text = bio.get('kz' if lang == "KZ" else 'ru', bio.get('ru', ''))
    gearbox_text = t("gearbox_automatic", lang) if instructor_detail.get('gearbox') == "AT" else t("gearbox_manual", lang)
    
    gender_text = t("gender_male", lang) if instructor_detail.get('gender') == "M" else t("gender_female", lang)
    
    # Получаем категории
    categories = instructor_detail.get('categories', [])
    category_codes = [cat.get('code', '') for cat in categories]
    category_text = ", ".join(category_codes) if category_codes else ""
    
    card_text = (
        f"{t('instructor_card_title', lang)}\n\n"
        f"<b>{instructor_detail['display_name']}</b>\n\n"
        f"{gender_text}\n"
        f"{gearbox_text}\n"
    )
    if category_text:
        card_text += f"📗 {t('choose_category', lang)}: {category_text}\n"
    if bio_text:
        card_text += f"\n{bio_text}\n"
    
    await state.update_data(selected_instructor=instructor_detail)
    await state.set_state(InstructorFlow.instructor_card)
    
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    pricing_button = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("instructor_view_pricing", lang))],
            [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
        ],
        resize_keyboard=True,
    )
    await message.answer(card_text, reply_markup=pricing_button, parse_mode="HTML")


@router.message(InstructorFlow.instructor_card)
async def instructors_view_pricing(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к списку инструкторов
        data = await state.get_data()
        instructors = data.get("instructors", [])
        if instructors:
            await state.set_state(InstructorFlow.instructor)
            opts = [f"{i['id']}: {i['display_name']}" for i in instructors]
            await message.answer(t("choose_instructor", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Проверяем, нажата ли кнопка "Посмотреть стоимость"
    if message.text != t("instructor_view_pricing", lang):
        # Если не кнопка, показываем снова карточку
        data = await state.get_data()
        instructor_detail = data.get("selected_instructor", {})
        bio = instructor_detail.get('bio', {})
        bio_text = bio.get('kz' if lang == "KZ" else 'ru', bio.get('ru', ''))
        gearbox_text = t("gearbox_automatic", lang) if instructor_detail.get('gearbox') == "AT" else t("gearbox_manual", lang)
        gender_text = t("gender_male", lang) if instructor_detail.get('gender') == "M" else t("gender_female", lang)
        categories = instructor_detail.get('categories', [])
        category_codes = [cat.get('code', '') for cat in categories]
        category_text = ", ".join(category_codes) if category_codes else ""
        
        card_text = (
            f"{t('instructor_card_title', lang)}\n\n"
            f"<b>{instructor_detail['display_name']}</b>\n\n"
            f"{gender_text}\n"
            f"{gearbox_text}\n"
        )
        if category_text:
            card_text += f"📗 {t('choose_category', lang)}: {category_text}\n"
        if bio_text:
            card_text += f"\n{bio_text}\n"
        
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        pricing_button = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=t("instructor_view_pricing", lang))],
                [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
            ],
            resize_keyboard=True,
        )
        await message.answer(card_text, reply_markup=pricing_button, parse_mode="HTML")
        return
    
    # Показываем все тарифы в одном экране
    data = await state.get_data()
    instructor_detail = data.get("selected_instructor", {})
    tariffs = instructor_detail.get('tariffs', [])
    
    if not tariffs:
        await message.answer(t("error_unknown", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    
    # Формируем текст со всеми тарифами
    tariffs_text = f"{t('instructor_tariffs_title', lang)}\n\n"
    
    # Разовые занятия
    single_tariffs = [t for t in tariffs if t.get('tariff_type') in ['SINGLE_HOUR', 'AUTODROM']]
    if single_tariffs:
        tariffs_text += f"<b>{t('tariff_single_title', lang)}</b>\n"
        for tariff_item in sorted(single_tariffs, key=lambda x: x.get('sort_order', 0)):
            tariff_type = tariff_item.get('tariff_type')
            price = tariff_item.get('price_kzt', 0)
            if tariff_type == 'SINGLE_HOUR':
                tariffs_text += f"• {t('tariff_single_hour', lang)} — {price:,} ₸\n"
            elif tariff_type == 'AUTODROM':
                tariffs_text += f"• {t('tariff_autodrom', lang)} — {price:,} ₸ / круг\n"
        tariffs_text += "\n"
    
    # Пакеты
    package_tariffs = [t for t in tariffs if t.get('tariff_type') in ['PACKAGE_5', 'PACKAGE_10', 'PACKAGE_15']]
    if package_tariffs:
        tariffs_text += f"<b>{t('tariff_packages_title', lang)}</b>\n"
        for tariff_item in sorted(package_tariffs, key=lambda x: x.get('sort_order', 0)):
            tariff_type = tariff_item.get('tariff_type')
            price = tariff_item.get('price_kzt', 0)
            name_ru = tariff_item.get('name_ru', '')
            name_kz = tariff_item.get('name_kz', '')
            name = name_kz if lang == "KZ" else name_ru
            
            if tariff_type == 'PACKAGE_5':
                tariff_label = t('tariff_package_5', lang)
            elif tariff_type == 'PACKAGE_10':
                tariff_label = t('tariff_package_10', lang)
            elif tariff_type == 'PACKAGE_15':
                tariff_label = t('tariff_package_15', lang)
            else:
                tariff_label = f"{tariff_type} — {name}"
            
            tariffs_text += f"• {tariff_label} — {price:,} ₸\n"
    
    await state.update_data(tariffs=tariffs)
    await state.set_state(InstructorFlow.tariff)
    
    # Формируем кнопки для выбора тарифа
    tariff_options = []
    for tariff_item in sorted(tariffs, key=lambda x: x.get('sort_order', 0)):
        tariff_type = tariff_item.get('tariff_type')
        price = tariff_item.get('price_kzt', 0)
        name_ru = tariff_item.get('name_ru', '')
        name_kz = tariff_item.get('name_kz', '')
        name = name_kz if lang == "KZ" else name_ru
        
        if tariff_type == 'SINGLE_HOUR':
            label = f"{t('tariff_single_hour', lang)} — {price:,} ₸"
        elif tariff_type == 'AUTODROM':
            label = f"{t('tariff_autodrom', lang)} — {price:,} ₸"
        elif tariff_type == 'PACKAGE_5':
            label = f"{t('tariff_package_5', lang)} — {price:,} ₸"
        elif tariff_type == 'PACKAGE_10':
            label = f"{t('tariff_package_10', lang)} — {price:,} ₸"
        elif tariff_type == 'PACKAGE_15':
            label = f"{t('tariff_package_15', lang)} — {price:,} ₸"
        else:
            label = f"{tariff_type} — {price:,} ₸"
        
        tariff_options.append(f"{tariff_item.get('id')}: {label}")
    
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    tariff_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=opt)] for opt in tariff_options
        ] + [
            [KeyboardButton(text=t("instructor_select_tariff", lang))],
            [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
        ],
        resize_keyboard=True,
    )
    
    await message.answer(tariffs_text, reply_markup=tariff_keyboard, parse_mode="HTML")


@router.message(InstructorFlow.tariff)
async def instructors_choose_tariff(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к карточке инструктора
        data = await state.get_data()
        instructor_detail = data.get("selected_instructor", {})
        bio = instructor_detail.get('bio', {})
        bio_text = bio.get('kz' if lang == "KZ" else 'ru', bio.get('ru', ''))
        gearbox_text = t("gearbox_automatic", lang) if instructor_detail.get('gearbox') == "AT" else t("gearbox_manual", lang)
        gender_text = t("gender_male", lang) if instructor_detail.get('gender') == "M" else t("gender_female", lang)
        categories = instructor_detail.get('categories', [])
        category_codes = [cat.get('code', '') for cat in categories]
        category_text = ", ".join(category_codes) if category_codes else ""
        
        card_text = (
            f"{t('instructor_card_title', lang)}\n\n"
            f"<b>{instructor_detail['display_name']}</b>\n\n"
            f"{gender_text}\n"
            f"{gearbox_text}\n"
        )
        if category_text:
            card_text += f"📗 {t('choose_category', lang)}: {category_text}\n"
        if bio_text:
            card_text += f"\n{bio_text}\n"
        
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        pricing_button = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=t("instructor_view_pricing", lang))],
                [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
            ],
            resize_keyboard=True,
        )
        await state.set_state(InstructorFlow.instructor_card)
        await message.answer(card_text, reply_markup=pricing_button, parse_mode="HTML")
        return
    
    # Проверяем, нажата ли кнопка "Выбрать тариф"
    if message.text == t("instructor_select_tariff", lang):
        data = await state.get_data()
        selected_tariff_id = data.get("selected_tariff_id")
        if not selected_tariff_id:
            # Если тариф не выбран, показываем снова список
            tariffs = data.get("tariffs", [])
            tariff_options = []
            for tariff_item in sorted(tariffs, key=lambda x: x.get('sort_order', 0)):
                tariff_type = tariff_item.get('tariff_type')
                price = tariff_item.get('price_kzt', 0)
                name_ru = tariff_item.get('name_ru', '')
                name_kz = tariff_item.get('name_kz', '')
                name = name_kz if lang == "KZ" else name_ru
                
                if tariff_type == 'SINGLE_HOUR':
                    label = f"{t('tariff_single_hour', lang)} — {price:,} ₸"
                elif tariff_type == 'AUTODROM':
                    label = f"{t('tariff_autodrom', lang)} — {price:,} ₸"
                elif tariff_type == 'PACKAGE_5':
                    label = f"{t('tariff_package_5', lang)} — {price:,} ₸"
                elif tariff_type == 'PACKAGE_10':
                    label = f"{t('tariff_package_10', lang)} — {price:,} ₸"
                elif tariff_type == 'PACKAGE_15':
                    label = f"{t('tariff_package_15', lang)} — {price:,} ₸"
                else:
                    label = f"{tariff_type} — {price:,} ₸"
                
                tariff_options.append(f"{tariff_item.get('id')}: {label}")
            
            from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
            tariff_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=opt)] for opt in tariff_options
                ] + [
                    [KeyboardButton(text=t("instructor_select_tariff", lang))],
                    [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
                ],
                resize_keyboard=True,
            )
            await message.answer(t("choose_tariff", lang), reply_markup=tariff_keyboard)
            return
        
        # Переход к форме заявки
        await state.set_state(InstructorFlow.name)
        await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))
        return
    
    # Обработка выбора тарифа
    data = await state.get_data()
    tariffs = data.get("tariffs", [])
    selected_tariff = None
    for tariff_item in tariffs:
        if message.text.startswith(f"{tariff_item.get('id')}:"):
            selected_tariff = tariff_item
            break
    
    if not selected_tariff:
        # Если тариф не распознан, показываем снова список
        tariff_options = []
        for tariff_item in sorted(tariffs, key=lambda x: x.get('sort_order', 0)):
            tariff_type = tariff_item.get('tariff_type')
            price = tariff_item.get('price_kzt', 0)
            
            if tariff_type == 'SINGLE_HOUR':
                label = f"{t('tariff_single_hour', lang)} — {price:,} ₸"
            elif tariff_type == 'AUTODROM':
                label = f"{t('tariff_autodrom', lang)} — {price:,} ₸"
            elif tariff_type == 'PACKAGE_5':
                label = f"{t('tariff_package_5', lang)} — {price:,} ₸"
            elif tariff_type == 'PACKAGE_10':
                label = f"{t('tariff_package_10', lang)} — {price:,} ₸"
            elif tariff_type == 'PACKAGE_15':
                label = f"{t('tariff_package_15', lang)} — {price:,} ₸"
            else:
                label = f"{tariff_type} — {price:,} ₸"
            
            tariff_options.append(f"{tariff_item.get('id')}: {label}")
        
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        tariff_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=opt)] for opt in tariff_options
            ] + [
                [KeyboardButton(text=t("instructor_select_tariff", lang))],
                [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
            ],
            resize_keyboard=True,
        )
        await message.answer(t("choose_tariff", lang), reply_markup=tariff_keyboard)
        return
    
    # Сохраняем выбранный тариф
    await state.update_data(selected_tariff_id=selected_tariff.get('id'), selected_tariff=selected_tariff)
    await send_event("register_button_clicked", {"instructor_id": data.get("selected_instructor", {}).get("id")}, bot_user_id=message.from_user.id)
    
    # Показываем подтверждение выбора тарифа и переходим к форме
    tariff_type = selected_tariff.get('tariff_type')
    price = selected_tariff.get('price_kzt', 0)
    
    if tariff_type == 'SINGLE_HOUR':
        tariff_label = t('tariff_single_hour', lang)
    elif tariff_type == 'AUTODROM':
        tariff_label = t('tariff_autodrom', lang)
    elif tariff_type == 'PACKAGE_5':
        tariff_label = t('tariff_package_5', lang)
    elif tariff_type == 'PACKAGE_10':
        tariff_label = t('tariff_package_10', lang)
    elif tariff_type == 'PACKAGE_15':
        tariff_label = t('tariff_package_15', lang)
    else:
        tariff_label = f"{tariff_type} — {price:,} ₸"
    
    await message.answer(f"✅ {t('instructor_select_tariff', lang)}: {tariff_label} — {price:,} ₸")
    await send_event("lead_form_opened", {"step": "name", "flow": "instructors"}, bot_user_id=message.from_user.id)
    await state.set_state(InstructorFlow.name)
    await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))


@router.message(InstructorFlow.name)
async def instructors_name(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору тарифа
        data = await state.get_data()
        tariffs = data.get("tariffs", [])
        if tariffs:
            await state.set_state(InstructorFlow.tariff)
            tariff_options = []
            for tariff_item in sorted(tariffs, key=lambda x: x.get('sort_order', 0)):
                tariff_type = tariff_item.get('tariff_type')
                price = tariff_item.get('price_kzt', 0)
                
                if tariff_type == 'SINGLE_HOUR':
                    label = f"{t('tariff_single_hour', lang)} — {price:,} ₸"
                elif tariff_type == 'AUTODROM':
                    label = f"{t('tariff_autodrom', lang)} — {price:,} ₸"
                elif tariff_type == 'PACKAGE_5':
                    label = f"{t('tariff_package_5', lang)} — {price:,} ₸"
                elif tariff_type == 'PACKAGE_10':
                    label = f"{t('tariff_package_10', lang)} — {price:,} ₸"
                elif tariff_type == 'PACKAGE_15':
                    label = f"{t('tariff_package_15', lang)} — {price:,} ₸"
                else:
                    label = f"{tariff_type} — {price:,} ₸"
                
                tariff_options.append(f"{tariff_item.get('id')}: {label}")
            
            from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
            tariff_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=opt)] for opt in tariff_options
                ] + [
                    [KeyboardButton(text=t("instructor_select_tariff", lang))],
                    [KeyboardButton(text=t("back", lang)), KeyboardButton(text=t("main_menu", lang))],
                ],
                resize_keyboard=True,
            )
            await message.answer(t("choose_tariff", lang), reply_markup=tariff_keyboard)
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(t("invalid_name", lang), reply_markup=back_keyboard(lang))
        return
    await state.update_data(name=name)
    await state.set_state(InstructorFlow.phone)
    await message.answer(t("enter_phone_contact", lang), reply_markup=phone_keyboard(lang))


@router.message(InstructorFlow.phone)
async def instructors_phone(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к вводу имени
        await state.set_state(InstructorFlow.name)
        await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))
        return
    
    # Обработка request_contact
    phone = None
    if message.contact:
        phone = normalize_phone(message.contact.phone_number)
    elif message.text:
        phone = normalize_phone(message.text)
    
    if not phone:
        await message.answer(t("invalid_phone", lang), reply_markup=phone_keyboard(lang))
        return
    
    await state.update_data(phone=phone)
    data = await state.get_data()
    instr = data["selected_instructor"]
    cities = data.get("cities", [])
    categories = data.get("categories", [])
    city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), str(data['city_id']))
    category_name = next((get_name_by_lang(c, lang) for c in categories if c["id"] == data.get('category_id')), "")
    
    # Определяем текст для пола
    gender_display = data.get('instructor_gender')
    if gender_display == "M":
        gender_text = "👨 Мужчина" if lang == "RU" else "👨 Еркек"
    elif gender_display == "F":
        gender_text = "👩 Женщина" if lang == "RU" else "👩 Әйел"
    else:
        gender_text = "⚖ Не имеет значения" if lang == "RU" else "⚖ Маңызды емес"
    
    # Определяем текст для КПП
    gearbox_display = "⚙️ Автомат" if data['gearbox'] == "AT" else "⚙️ Механика"
    if lang == "KZ":
        gearbox_display = "⚙️ Автомат" if data['gearbox'] == "AT" else "⚙️ Механика"
    
    # Получаем выбранный тариф
    selected_tariff = data.get("selected_tariff", {})
    tariff_type = selected_tariff.get('tariff_type', '')
    tariff_price = selected_tariff.get('price_kzt', 0)
    
    if tariff_type == 'SINGLE_HOUR':
        tariff_label = t('tariff_single_hour', lang)
    elif tariff_type == 'AUTODROM':
        tariff_label = t('tariff_autodrom', lang)
    elif tariff_type == 'PACKAGE_5':
        tariff_label = t('tariff_package_5', lang)
    elif tariff_type == 'PACKAGE_10':
        tariff_label = t('tariff_package_10', lang)
    elif tariff_type == 'PACKAGE_15':
        tariff_label = t('tariff_package_15', lang)
    else:
        tariff_label = tariff_type
    
    confirm_text_ru = (
        f"{t('confirm_data', lang)}\n\n"
        f"Город: {city_name}\n"
        f"Категория: {category_name}\n"
        f"КПП: {gearbox_display}\n"
        f"Пол инструктора: {gender_text}\n"
        f"Инструктор: {instr['display_name']}\n"
        f"Тариф: {tariff_label} — {tariff_price:,} ₸\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {phone}"
    )
    confirm_text_kz = (
        f"{t('confirm_data', lang)}\n\n"
        f"Қала: {city_name}\n"
        f"Санат: {category_name}\n"
        f"КПП: {gearbox_display}\n"
        f"Нұсқаушының жынысы: {gender_text}\n"
        f"Нұсқаушы: {instr['display_name']}\n"
        f"Тариф: {tariff_label} — {tariff_price:,} ₸\n"
        f"Аты: {data['name']}\n"
        f"Телефон: {phone}"
    )
    text = confirm_text_kz if lang == "KZ" else confirm_text_ru
    await state.set_state(InstructorFlow.confirm)
    await message.answer(text, reply_markup=confirm_keyboard(lang))


@router.message(InstructorFlow.confirm, F.text.in_(["✅ Всё верно", "✅ Барлығы дұрыс"]))
async def instructors_confirm(message: Message, state: FSMContext):
    lang = await get_language(state)
    data = await state.get_data()
    instr = data["selected_instructor"]
    api = ApiClient()
    payload = {
        "type": "INSTRUCTOR",
        "language": lang,
        "bot_user": {
            "telegram_user_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language": lang,
        },
        "contact": {"name": data["name"], "phone": data["phone"]},
        "payload": {
            "city_id": data["city_id"],
            "category_id": data.get("category_id"),
            "gearbox": data["gearbox"],
            "preferred_instructor_gender": data.get("instructor_gender"),
            "instructor_id": instr["id"],
            "instructor_tariff_id": data.get("selected_tariff_id"),
            "instructor_tariff_price_kzt": data.get("selected_tariff", {}).get("price_kzt"),
        },
    }
    try:
        lead_response = await api.create_lead(payload)
        lead_id = lead_response.get("id") if isinstance(lead_response, dict) else None
    except Exception as exc:
        await api.close()
        await handle_api_error(exc, lang, message, state)
        return
    await api.close()
    await send_event("lead_submitted", {"type": "INSTRUCTOR"}, bot_user_id=message.from_user.id, lead_id=lead_id)
    
    # Получаем название категории для WhatsApp сообщения
    categories = data.get("categories", [])
    category_name = ""
    for c in categories:
        if c.get("id") == data.get("category_id"):
            category_name = get_name_by_lang(c, lang)
            break
    
    # Показываем благодарность согласно ТЗ
    await message.answer(t("thank_you", lang), reply_markup=main_menu(lang))
    
    # Генерируем WhatsApp ссылку с шаблоном (автоматически открывается)
    wa_link = build_wa_link_instructor(instr, data["name"], data["phone"], category_name, lang)
    if wa_link:
        await send_event("whatsapp_opened", {"flow": "instructors", "instructor_id": instr["id"]}, bot_user_id=message.from_user.id)
        # Отправляем ссылку для автоматического открытия WhatsApp
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="Открыть WhatsApp" if lang == "RU" else "WhatsApp ашу",
            url=wa_link
        )]])
        await message.answer(
            "Нажмите на кнопку, чтобы открыть WhatsApp" if lang == "RU" else "WhatsApp ашу үшін батырманы басыңыз",
            reply_markup=keyboard
        )
    
    await state.clear()


@router.message(InstructorFlow.confirm)
async def instructors_confirm_any(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Обработка кнопки "Исправить"
    fix_text_ru = t("fix", "RU")
    fix_text_kz = t("fix", "KZ")
    if message.text in [fix_text_ru, fix_text_kz]:
        # Возврат к вводу имени
        await state.set_state(InstructorFlow.name)
        await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))
        return
    
    # Если не "Всё верно" и не "Исправить", показываем снова подтверждение
    data = await state.get_data()
    instr = data["selected_instructor"]
    cities = data.get("cities", [])
    categories = data.get("categories", [])
    city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), str(data['city_id']))
    category_name = next((get_name_by_lang(c, lang) for c in categories if c["id"] == data.get('category_id')), "")
    
    gender_display = data.get('instructor_gender')
    if gender_display == "M":
        gender_text = "👨 Мужчина" if lang == "RU" else "👨 Еркек"
    elif gender_display == "F":
        gender_text = "👩 Женщина" if lang == "RU" else "👩 Әйел"
    else:
        gender_text = "⚖ Не имеет значения" if lang == "RU" else "⚖ Маңызды емес"
    
    gearbox_display = "⚙️ Автомат" if data['gearbox'] == "AT" else "⚙️ Механика"
    
    confirm_text_ru = (
        f"{t('confirm_data', lang)}\n\n"
        f"Город: {city_name}\n"
        f"Категория: {category_name}\n"
        f"КПП: {gearbox_display}\n"
        f"Пол инструктора: {gender_text}\n"
        f"Инструктор: {instr['display_name']}\n"
        f"Тариф: {tariff_label} — {tariff_price:,} ₸\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}"
    )
    confirm_text_kz = (
        f"{t('confirm_data', lang)}\n\n"
        f"Қала: {city_name}\n"
        f"Санат: {category_name}\n"
        f"КПП: {gearbox_display}\n"
        f"Нұсқаушының жынысы: {gender_text}\n"
        f"Нұсқаушы: {instr['display_name']} ({instr['price_kzt']} KZT)\n"
        f"Аты: {data['name']}\n"
        f"Телефон: {data['phone']}"
    )
    text = confirm_text_kz if lang == "KZ" else confirm_text_ru
    await message.answer(text, reply_markup=confirm_keyboard(lang))

