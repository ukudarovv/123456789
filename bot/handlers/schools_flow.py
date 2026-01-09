from typing import Optional
import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import DEFAULT_LANGUAGE
from i18n import t
from keyboards.common import main_menu, back_keyboard, choices_keyboard, phone_keyboard, confirm_keyboard
from services.api import ApiClient, ApiClientError, ApiServerError, ApiTimeoutError, ApiNetworkError
from services.analytics import send_event
from states_school import SchoolFlow
from utils.validators import normalize_phone
from utils.whatsapp import build_wa_link_school

router = Router()

# Флаги обработки для предотвращения параллельного выполнения обработчика школы
_processing_schools = set()


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


def format_choice_option(index: int, name: str) -> str:
    """Форматировать опцию выбора - просто название без номера"""
    # Убираем лишние пробелы из имени
    return name.strip()


def find_item_by_text(items: list, text: str, lang: str) -> dict:
    """Найти элемент по тексту кнопки (точное совпадение или по имени)"""
    text = text.strip()
    # Ищем по точному совпадению имени
    for item in items:
        name = get_name_by_lang(item, lang).strip()
        if text == name:
            return item
    # Если не нашли по точному совпадению, пробуем найти по частичному совпадению
    for item in items:
        name = get_name_by_lang(item, lang).strip()
        if text in name or name in text:
            return item
    return None


def get_tariff_name(tariff_item: dict, lang: str) -> str:
    """Получить название тарифа на нужном языке из данных API"""
    if lang == "KZ":
        return tariff_item.get('name_kz') or tariff_item.get('name_ru') or tariff_item.get('code', '')
    return tariff_item.get('name_ru') or tariff_item.get('code', '')


def extract_available_categories(tariffs: list, all_categories: list) -> list:
    """Извлечь уникальные категории из тарифов + универсальные (categories пусто)"""
    category_ids = set()
    has_universal = False
    
    for tariff in tariffs:
        category_ids_list = tariff.get('category_ids', [])
        if category_ids_list:
            for cat_id in category_ids_list:
                category_ids.add(cat_id)
        else:
            has_universal = True
    
    # Получаем категории из списка всех категорий
    result = []
    for cat in all_categories:
        if cat['id'] in category_ids:
            result.append(cat)
    
    # Если есть универсальные тарифы, добавляем все категории
    if has_universal:
        for cat in all_categories:
            if cat['id'] not in category_ids:
                result.append(cat)
    
    return result


def extract_available_formats(tariffs: list, category_id: int, all_formats: list) -> list:
    """Извлечь уникальные форматы из тарифов для выбранной категории + универсальные"""
    format_ids = set()
    has_universal = False
    
    for tariff in tariffs:
        tariff_category_ids = tariff.get('category_ids', [])
        # Тариф подходит, если содержит выбранную категорию или не привязан к категориям (универсальный)
        if category_id in tariff_category_ids or not tariff_category_ids:
            format_id = tariff.get('training_format_id')
            if format_id:
                format_ids.add(format_id)
            else:
                has_universal = True
    
    # Получаем форматы из списка всех форматов
    result = []
    for fmt in all_formats:
        if fmt['id'] in format_ids:
            result.append(fmt)
    
    # Если есть универсальные тарифы, добавляем все форматы
    if has_universal:
        for fmt in all_formats:
            if fmt['id'] not in format_ids:
                result.append(fmt)
    
    return result


def extract_available_gearboxes(tariffs: list, category_id: int, format_id: int) -> list:
    """Извлечь уникальные значения КПП из тарифов для выбранной категории и формата"""
    gearbox_set = set()
    
    for tariff in tariffs:
        tariff_category_ids = tariff.get('category_ids', [])
        tariff_format_id = tariff.get('training_format_id')
        gearbox = tariff.get('gearbox')
        
        # Тариф подходит, если содержит выбранную категорию (или не привязан) и format_id совпадает или null
        category_match = category_id in tariff_category_ids or not tariff_category_ids
        format_match = tariff_format_id == format_id or tariff_format_id is None
        
        if category_match and format_match and gearbox:
            gearbox_set.add(gearbox)
    
    return sorted(list(gearbox_set))


def extract_available_times(tariffs: list, category_id: int, format_id: int, gearbox: str, all_time_slots: list) -> list:
    """Извлечь уникальные времена из тарифов для выбранной категории, формата и КПП"""
    time_ids = set()
    
    for tariff in tariffs:
        tariff_category_ids = tariff.get('category_ids', [])
        tariff_format_id = tariff.get('training_format_id')
        tariff_gearbox = tariff.get('gearbox')
        
        # Тариф подходит, если содержит выбранную категорию (или не привязан), format_id совпадает или null, и gearbox совпадает или null
        category_match = category_id in tariff_category_ids or not tariff_category_ids
        format_match = tariff_format_id == format_id or tariff_format_id is None
        gearbox_match = tariff_gearbox == gearbox or tariff_gearbox is None
        
        if category_match and format_match and gearbox_match:
            # Получаем времена из training_time_ids
            time_ids_list = tariff.get('training_time_ids', [])
            for time_id in time_ids_list:
                time_ids.add(time_id)
    
    # Получаем времена из списка всех времен
    result = []
    for time_slot in all_time_slots:
        if time_slot['id'] in time_ids:
            result.append(time_slot)
    
    return result


def all_tariffs_without_gearbox(tariffs: list, category_id: int, format_id: int) -> bool:
    """Проверяет, все ли тарифы без указания КПП"""
    matching_tariffs = []
    for tariff in tariffs:
        tariff_category_ids = tariff.get('category_ids', [])
        tariff_format_id = tariff.get('training_format_id')
        category_match = category_id in tariff_category_ids or not tariff_category_ids
        format_match = tariff_format_id == format_id or tariff_format_id is None
        if category_match and format_match:
            matching_tariffs.append(tariff)
    
    if not matching_tariffs:
        return False
    
    # Проверяем, что у всех тарифов gearbox is None или отсутствует
    return all(t.get('gearbox') is None for t in matching_tariffs)


def all_tariffs_without_time(tariffs: list, category_id: int, format_id: int, gearbox: Optional[str] = None) -> bool:
    """Проверяет, все ли тарифы без указания времени"""
    matching_tariffs = []
    for tariff in tariffs:
        tariff_category_ids = tariff.get('category_ids', [])
        tariff_format_id = tariff.get('training_format_id')
        tariff_gearbox = tariff.get('gearbox')
        category_match = category_id in tariff_category_ids or not tariff_category_ids
        format_match = tariff_format_id == format_id or tariff_format_id is None
        gearbox_match = (gearbox is None and tariff_gearbox is None) or tariff_gearbox == gearbox
        if category_match and format_match and gearbox_match:
            matching_tariffs.append(tariff)
    
    if not matching_tariffs:
        return False
    
    # Проверяем, что у всех тарифов training_time_ids пусто
    return all(not tariff.get('training_time_ids') for tariff in matching_tariffs)


async def _process_gearbox_selection(message: Message, state: FSMContext, lang: str, fmt_id: int):
    """Обработать выбор КПП: автоматически выбрать, если доступен только один вариант, или показать выбор"""
    data = await state.get_data()
    tariffs = data.get("tariffs", [])
    category_id = data.get("category_id")
    
    # Проверяем, все ли тарифы без КПП
    if all_tariffs_without_gearbox(tariffs, category_id, fmt_id):
        # Все тарифы без КПП - пропускаем выбор КПП, устанавливаем gearbox=None
        await state.update_data(gearbox=None)
        await _process_time_selection(message, state, lang, fmt_id)
        return
    
    # Извлекаем доступные КПП из тарифов
    available_gearboxes = extract_available_gearboxes(tariffs, category_id, fmt_id)
    
    if not available_gearboxes:
        # Если нет доступных КПП, переходим к выбору времени (старая логика)
        await _process_time_selection(message, state, lang, fmt_id)
        return
    
    # Если доступен только один вариант КПП - автоматически выбираем его
    if len(available_gearboxes) == 1:
        selected_gearbox = available_gearboxes[0]
        await send_event("gearbox_selected", {"gearbox": selected_gearbox}, bot_user_id=message.from_user.id)
        await state.update_data(gearbox=selected_gearbox)
        await _process_time_selection(message, state, lang, fmt_id)
    else:
        # Показываем выбор КПП
        await state.set_state(SchoolFlow.gearbox)
        gearbox_options = []
        for gb in available_gearboxes:
            if gb == "AT":
                gearbox_options.append(t("gearbox_automatic", lang))
            elif gb == "MT":
                gearbox_options.append(t("gearbox_manual", lang))
        await message.answer(t("gearbox_prompt", lang), reply_markup=choices_keyboard(gearbox_options, lang))


async def _load_and_show_tariffs(message: Message, state: FSMContext, lang: str, training_time_id: Optional[int] = None):
    """Загрузить и показать тарифы с учетом всех фильтров"""
    data = await state.get_data()
    school_id = data.get("school_id")
    category_id = data.get("category_id")
    training_format_id = data.get("training_format_id")
    gearbox = data.get("gearbox")
    
    api = ApiClient()
    try:
        detail = await api.get_school_detail(
            school_id,
            category_id=category_id,
            training_format_id=training_format_id,
            training_time_id=training_time_id,
            gearbox=gearbox,
            language=lang
        )
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    tariffs = detail.get("tariffs", [])
    if not tariffs:
        await message.answer(t("no_tariffs", lang) if hasattr(t, "no_tariffs") else "Нет доступных тарифов", reply_markup=main_menu(lang))
        await state.clear()
        return
    
    await state.update_data(tariffs=tariffs)
    
    # Если остался только один тариф, автоматически выбираем его и показываем описание
    if len(tariffs) == 1:
        tariff = tariffs[0]
        await send_event("tariff_selected", {"tariff_name": tariff.get('name_ru') or tariff.get('name_kz', '')}, bot_user_id=message.from_user.id)
        await state.update_data(selected_tariff=tariff)
        
        # Получаем описание тарифа
        tariff_description = tariff.get('description_kz' if lang == "KZ" else 'description_ru', tariff.get('description_ru', ''))
        tariff_name = get_tariff_name(tariff, lang)
        tariff_price = tariff.get('price_kzt', 0)
        
        # Показываем описание тарифа, если оно есть, или цену, если описания нет
        if tariff_description:
            description_text = (
                f"<b>{tariff_name} — {tariff_price:,} ₸</b>\n\n"
                f"{tariff_description}"
            )
            await message.answer(description_text, parse_mode="HTML")
        else:
            # Если нет описания, показываем только цену
            price_text = f"<b>{tariff_name} — {tariff_price:,} ₸</b>"
            await message.answer(price_text, parse_mode="HTML")
        
        await send_event("lead_form_opened", {"step": "name", "flow": "schools"}, bot_user_id=message.from_user.id)
        await state.set_state(SchoolFlow.name)
        await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))
        return
    
    # Если тарифов больше одного, показываем клавиатуру для выбора
    opts = [format_choice_option(i, get_tariff_name(tariff_item, lang)) for i, tariff_item in enumerate(tariffs)]
    await state.set_state(SchoolFlow.tariff)
    await message.answer(t("choose_tariff", lang), reply_markup=choices_keyboard(opts, lang))


async def _process_time_selection(message: Message, state: FSMContext, lang: str, fmt_id: int):
    """Обработать выбор времени обучения"""
    data = await state.get_data()
    tariffs = data.get("tariffs", [])
    category_id = data.get("category_id")
    gearbox = data.get("gearbox")
    
    # Проверяем, все ли тарифы без времени
    if all_tariffs_without_time(tariffs, category_id, fmt_id, gearbox):
        # Все тарифы без времени - пропускаем выбор времени, сразу показываем тарифы
        await state.update_data(training_time=None, training_time_id=None, training_time_display="")
        await _load_and_show_tariffs(message, state, lang, training_time_id=None)
        return
    
    # Загружаем все времена для извлечения доступных
    api = ApiClient()
    try:
        all_time_slots = await api.get_training_time_slots()
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    # Извлекаем доступные времена из тарифов для выбранной категории, формата и КПП
    available_times = extract_available_times(tariffs, category_id, fmt_id, gearbox, all_time_slots)
    
    if not available_times:
        await message.answer(t("no_times", lang) if hasattr(t, "no_times") else "Нет доступного времени обучения", reply_markup=main_menu(lang))
        await state.clear()
        return
    
    await state.update_data(training_time_slots=available_times)
    time_options = []
    for i, slot in enumerate(available_times):
        name = slot.get('name_kz' if lang == "KZ" else 'name_ru', slot.get('name_ru', ''))
        emoji = slot.get('emoji', '')
        time_range = slot.get('time_range_kz' if lang == "KZ" else 'time_range_ru', slot.get('time_range_ru', ''))
        
        # Убираем лишние пробелы
        name = name.strip()
        emoji = emoji.strip() if emoji else ''
        
        if time_range:
            option_text = format_choice_option(i, f"{emoji} {name} ({time_range})".strip())
        else:
            option_text = format_choice_option(i, f"{emoji} {name}".strip())
        time_options.append(option_text)
    
    await state.set_state(SchoolFlow.training_time)
    await message.answer(t("training_time_question", lang), reply_markup=choices_keyboard(time_options, lang))


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


@router.message(Command("schools"))
@router.message(F.text.in_(["Автошколы", "Автошколалар", "автошколы"]))
async def schools_start(message: Message, state: FSMContext):
    # Очищаем текущее состояние перед началом нового потока
    await state.clear()
    lang = await get_language(state)
    await send_event("flow_selected", {"flow": "schools"}, bot_user_id=message.from_user.id)
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
    await state.set_state(SchoolFlow.city)
    options = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(cities)]
    await state.update_data(cities=cities, language=lang)
    await message.answer(t("choose_city", lang), reply_markup=choices_keyboard(options, lang))


@router.message(SchoolFlow.city)
async def schools_choose_city(message: Message, state: FSMContext):
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
    selected_city = find_item_by_text(cities, message.text, lang)
    if not selected_city:
        options = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(cities)]
        await message.answer(t("choose_city", lang), reply_markup=choices_keyboard(options, lang))
        return
    city_id = selected_city["id"]
    await send_event("city_selected", {"city_id": city_id}, bot_user_id=message.from_user.id)
    api = ApiClient()
    try:
        schools = await api.get_schools(city_id=city_id)
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    if not schools:
        await message.answer(t("no_schools", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    await state.update_data(city_id=city_id, schools=schools)
    opts = [format_choice_option(i, get_name_by_lang(s, lang)) for i, s in enumerate(schools)]
    await state.set_state(SchoolFlow.school)
    await message.answer(t("choose_school", lang), reply_markup=choices_keyboard(opts, lang))


@router.message(SchoolFlow.category)
async def schools_choose_category(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору школы
        data = await state.get_data()
        schools = data.get("schools", [])
        if schools:
            await state.set_state(SchoolFlow.school)
            opts = []
            for s in schools:
                opts.append(format_choice_option(len(opts), get_name_by_lang(s, lang)))
            await message.answer(t("choose_school", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    data = await state.get_data()
    categories = data.get("categories", [])
    tariffs = data.get("tariffs", [])
    selected_category = find_item_by_text(categories, message.text, lang)
    if not selected_category:
        opts = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(categories)]
        await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))
        return
    category_id = selected_category["id"]
    
    await send_event("category_selected", {"category_id": category_id}, bot_user_id=message.from_user.id)
    
    # Загружаем все форматы для извлечения доступных
    api = ApiClient()
    try:
        all_formats = await api.get_training_formats()
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    # Извлекаем доступные форматы из тарифов для выбранной категории
    available_formats = extract_available_formats(tariffs, category_id, all_formats)
    
    if not available_formats:
        await message.answer(t("no_formats", lang) if hasattr(t, "no_formats") else "Нет доступных форматов", reply_markup=main_menu(lang))
        await state.clear()
        return
    
    await state.update_data(category_id=category_id, formats=available_formats)
    
    # Перезагружаем тарифы школы с учетом выбранной категории для правильного извлечения КПП
    school_id = data.get("school_id")
    if school_id:
        api = ApiClient()
        try:
            detail = await api.get_school_detail(school_id, category_id=category_id, language=lang)
            tariffs = detail.get("tariffs", [])
            await state.update_data(tariffs=tariffs)
        except Exception:
            pass
        finally:
            await api.close()
    
    # Если доступен только один формат - автоматически выбираем его
    if len(available_formats) == 1:
        selected_format = available_formats[0]
        fmt_id = selected_format["id"]
        await send_event("format_selected", {"training_format_id": fmt_id}, bot_user_id=message.from_user.id)
        await state.update_data(training_format_id=fmt_id)
        
        # Перезагружаем тарифы с учетом формата для правильного извлечения КПП
        if school_id:
            api = ApiClient()
            try:
                detail = await api.get_school_detail(school_id, category_id=category_id, training_format_id=fmt_id, language=lang)
                tariffs = detail.get("tariffs", [])
                await state.update_data(tariffs=tariffs)
            except Exception:
                pass
            finally:
                await api.close()
        
        # Переходим к анализу КПП
        await _process_gearbox_selection(message, state, lang, fmt_id)
    else:
        # Показываем выбор формата
        opts = [format_choice_option(i, get_name_by_lang(f, lang)) for i, f in enumerate(available_formats)]
        await state.set_state(SchoolFlow.training_format)
        await message.answer(t("choose_format", lang), reply_markup=choices_keyboard(opts, lang))


@router.message(SchoolFlow.training_format)
async def schools_choose_format(message: Message, state: FSMContext):
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
            await state.set_state(SchoolFlow.category)
            opts = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(categories)]
            await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    data = await state.get_data()
    formats = data.get("formats", [])
    selected_format = find_item_by_text(formats, message.text, lang)
    if not selected_format:
        opts = [format_choice_option(i, get_name_by_lang(f, lang)) for i, f in enumerate(formats)]
        await message.answer(t("choose_format", lang), reply_markup=choices_keyboard(opts, lang))
        return
    fmt_id = selected_format["id"]
    
    await send_event("format_selected", {"training_format_id": fmt_id}, bot_user_id=message.from_user.id)
    await state.update_data(training_format_id=fmt_id)
    
    # Перезагружаем тарифы с учетом формата для правильного извлечения КПП
    school_id = data.get("school_id")
    category_id = data.get("category_id")
    if school_id and category_id:
        api = ApiClient()
        try:
            detail = await api.get_school_detail(school_id, category_id=category_id, training_format_id=fmt_id)
            tariffs = detail.get("tariffs", [])
            await state.update_data(tariffs=tariffs)
        except Exception:
            pass
        finally:
            await api.close()
    
    # Переходим к анализу КПП
    await _process_gearbox_selection(message, state, lang, fmt_id)


@router.message(SchoolFlow.gearbox)
async def schools_choose_gearbox(message: Message, state: FSMContext):
    """Обработка выбора КПП"""
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору формата
        data = await state.get_data()
        formats = data.get("formats", [])
        if formats:
            await state.set_state(SchoolFlow.training_format)
            opts = [format_choice_option(i, get_name_by_lang(f, lang)) for i, f in enumerate(formats)]
            await message.answer(t("choose_format", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Определяем выбранный КПП по тексту сообщения
    gearbox_text = message.text.strip()
    selected_gearbox = None
    
    automatic_text = t("gearbox_automatic", lang)
    manual_text = t("gearbox_manual", lang)
    
    if automatic_text.lower() in gearbox_text.lower() or "автомат" in gearbox_text.lower():
        selected_gearbox = "AT"
    elif manual_text.lower() in gearbox_text.lower() or "механик" in gearbox_text.lower():
        selected_gearbox = "MT"
    
    if not selected_gearbox:
        # Неверный выбор, показываем снова
        data = await state.get_data()
        tariffs = data.get("tariffs", [])
        category_id = data.get("category_id")
        fmt_id = data.get("training_format_id")
        available_gearboxes = extract_available_gearboxes(tariffs, category_id, fmt_id)
        gearbox_options = []
        for gb in available_gearboxes:
            if gb == "AT":
                gearbox_options.append(t("gearbox_automatic", lang))
            elif gb == "MT":
                gearbox_options.append(t("gearbox_manual", lang))
        await message.answer(t("gearbox_prompt", lang), reply_markup=choices_keyboard(gearbox_options, lang))
        return
    
    await send_event("gearbox_selected", {"gearbox": selected_gearbox}, bot_user_id=message.from_user.id)
    await state.update_data(gearbox=selected_gearbox)
    
    # Переходим к выбору времени обучения
    fmt_id = (await state.get_data()).get("training_format_id")
    await _process_time_selection(message, state, lang, fmt_id)


@router.message(SchoolFlow.school)
async def schools_choose_school(message: Message, state: FSMContext):
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
            await state.set_state(SchoolFlow.city)
            options = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(cities)]
            await message.answer(t("choose_city", lang), reply_markup=choices_keyboard(options, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    data = await state.get_data()
    schools = data.get("schools", [])
    selected_school = find_item_by_text(schools, message.text, lang)
    if not selected_school:
        opts = [format_choice_option(i, get_name_by_lang(s, lang)) for i, s in enumerate(schools)]
        await message.answer(t("choose_school", lang), reply_markup=choices_keyboard(opts, lang))
        return
    school_id = selected_school["id"]
    
    # СТРОГАЯ защита от дублирования: используем флаг обработки на основе user_id и school_id
    processing_key = f"{message.from_user.id}_{school_id}"
    
    # Если уже обрабатываем эту школу для этого пользователя - выходим немедленно
    if processing_key in _processing_schools:
        return
    
    # Помечаем, что начинаем обработку
    _processing_schools.add(processing_key)
    
    try:
        
        await send_event("school_selected", {"school_id": school_id}, bot_user_id=message.from_user.id)
        
        # Загружаем детали школы с тарифами БЕЗ фильтров (категория еще не выбрана)
        # Фильтры будут применены позже при выборе категории и формата
        api = ApiClient()
        try:
            detail = await api.get_school_detail(school_id, language=lang)
        except Exception as e:
            await api.close()
            await handle_api_error(e, lang, message, state)
            return
        await api.close()
        
        tariffs = detail.get("tariffs", [])
        if not tariffs:
            await message.answer(t("no_tariffs", lang) if hasattr(t, "no_tariffs") else "Нет доступных тарифов", reply_markup=main_menu(lang))
            await state.clear()
            return
        
        # Формируем и показываем описание школы - просто название и описание из БД
        school_name = get_name_by_lang(detail.get('name', {}), lang) or detail.get('name', {}).get('ru', '')
        # Описание теперь приходит как строка на нужном языке из бэкенда
        description_text = detail.get('description', '')
        if description_text:
            description_text = description_text.strip()
        else:
            description_text = ""
        
        cities = data.get("cities", [])
        city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), "")
        
        # Просто показываем название школы и описание из БД
        card_text = f"🏫 <b>Автошкола «{school_name}»</b>"
        if city_name:
            card_text += f" ({city_name})"
        card_text += "\n\n"
        
        if description_text:
            card_text += f"{description_text}"
        
        # Показываем описание школы (только один раз)
        await message.answer(card_text, parse_mode="HTML")
        
        # Загружаем все категории для извлечения доступных
        api = ApiClient()
        try:
            all_categories = await api.get_categories()
        except Exception as e:
            await api.close()
            await handle_api_error(e, lang, message, state)
            return
        await api.close()
        
        # Извлекаем доступные категории из тарифов
        available_categories = extract_available_categories(tariffs, all_categories)
        
        if not available_categories:
            await message.answer(t("no_categories", lang) if hasattr(t, "no_categories") else "Нет доступных категорий", reply_markup=main_menu(lang))
            await state.clear()
            return
        
        await state.update_data(school_id=school_id, school_detail=detail, tariffs=tariffs, categories=available_categories)
        opts = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(available_categories)]
        await state.set_state(SchoolFlow.category)
        await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))
    finally:
        # Снимаем флаг обработки
        _processing_schools.discard(processing_key)


# Обработчик school_card больше не используется в новом потоке
# @router.message(SchoolFlow.school_card)
async def schools_register_button_old(message: Message, state: FSMContext):
    """Обработка нажатия кнопки 'Записаться' на карточке школы"""
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору школы
        data = await state.get_data()
        schools = data.get("schools", [])
        if schools:
            await state.set_state(SchoolFlow.school)
            opts = []
            for s in schools:
                opts.append(format_choice_option(len(opts), get_name_by_lang(s, lang)))
            await message.answer(t("choose_school", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Проверяем, что нажата кнопка "Записаться"
    register_text_ru = t("register_button", "RU")
    register_text_kz = t("register_button", "KZ")
    if message.text not in [register_text_ru, register_text_kz]:
        # Если не кнопка "Записаться", показываем снова карточку
        data = await state.get_data()
        detail = data.get("school_detail", {})
        school_name = get_name_by_lang(detail.get('name', {}), lang) or detail.get('name', {}).get('ru', '')
        # Описание теперь приходит как строка на нужном языке из бэкенда
        description_text = detail.get('description', '')
        if description_text:
            description_text = description_text.strip()
        else:
            description_text = ""
        
        cities = data.get("cities", [])
        city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), "")
        
        # Просто показываем название школы и описание из БД
        card_text = f"🏫 <b>Автошкола «{school_name}»</b>"
        if city_name:
            card_text += f" ({city_name})"
        card_text += "\n\n"
        
        if description_text:
            card_text += f"{description_text}"
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        register_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=t("register_button", lang))]],
            resize_keyboard=True,
        )
        await message.answer(card_text, reply_markup=register_keyboard, parse_mode="HTML")
        return
    
    # Нажата кнопка "Записаться" - переходим к выбору времени обучения
    data = await state.get_data()
    await send_event("register_button_clicked", {"school_id": data.get("school_id")}, bot_user_id=message.from_user.id)
    
    # Загружаем время обучения из API
    api = ApiClient()
    try:
        time_slots = await api.get_training_time_slots()
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    if not time_slots:
        await message.answer(t("error_unknown", lang), reply_markup=main_menu(lang))
        await state.clear()
        return
    
    # Формируем опции времени обучения из API
    time_options = []
    for i, slot in enumerate(time_slots):
        name = slot.get('name_kz' if lang == "KZ" else 'name_ru', slot.get('name_ru', ''))
        emoji = slot.get('emoji', '')
        time_range = slot.get('time_range_kz' if lang == "KZ" else 'time_range_ru', slot.get('time_range_ru', ''))
        
        # Убираем лишние пробелы
        name = name.strip()
        emoji = emoji.strip() if emoji else ''
        
        if time_range:
            option_text = format_choice_option(i, f"{emoji} {name} ({time_range})".strip())
        else:
            option_text = format_choice_option(i, f"{emoji} {name}".strip())
        time_options.append(option_text)
    
    await state.update_data(training_time_slots=time_slots)
    await state.set_state(SchoolFlow.training_time)
    await message.answer(t("training_time_question", lang), reply_markup=choices_keyboard(time_options, lang))


@router.message(SchoolFlow.training_time)
async def schools_choose_training_time(message: Message, state: FSMContext):
    """Обработка выбора времени обучения"""
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору КПП (если был выбор) или формата (если КПП был выбран автоматически)
        data = await state.get_data()
        gearbox = data.get("gearbox")
        formats = data.get("formats", [])
        tariffs = data.get("tariffs", [])
        category_id = data.get("category_id")
        fmt_id = data.get("training_format_id")
        
        # Проверяем, был ли выбор КПП (если доступны оба варианта)
        available_gearboxes = extract_available_gearboxes(tariffs, category_id, fmt_id) if fmt_id else []
        
        if len(available_gearboxes) > 1 and gearbox:
            # Возврат к выбору КПП
            await state.set_state(SchoolFlow.gearbox)
            gearbox_options = []
            for gb in available_gearboxes:
                if gb == "AT":
                    gearbox_options.append(t("gearbox_automatic", lang))
                elif gb == "MT":
                    gearbox_options.append(t("gearbox_manual", lang))
            await message.answer(t("gearbox_prompt", lang), reply_markup=choices_keyboard(gearbox_options, lang))
        elif formats:
            # Возврат к выбору формата
            await state.set_state(SchoolFlow.training_format)
            opts = [format_choice_option(i, get_name_by_lang(f, lang)) for i, f in enumerate(formats)]
            await message.answer(t("choose_format", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Проверяем выбор времени из загруженных слотов
    data = await state.get_data()
    time_slots = data.get("training_time_slots", [])
    
    # Ищем по тексту сообщения
    selected_time_slot = None
    text = message.text.strip()
    for slot in time_slots:
        name = slot.get('name_kz' if lang == "KZ" else 'name_ru', slot.get('name_ru', '')).strip()
        emoji = slot.get('emoji', '').strip() if slot.get('emoji') else ''
        time_range = slot.get('time_range_kz' if lang == "KZ" else 'time_range_ru', slot.get('time_range_ru', '')).strip()
        
        # Проверяем точное совпадение
        if time_range:
            option_text = f"{emoji} {name} ({time_range})".strip()
        else:
            option_text = f"{emoji} {name}".strip()
        
        if text == option_text:
            selected_time_slot = slot
            break
    
    if not selected_time_slot:
        # Неверный выбор, показываем снова
        time_options = []
        for i, slot in enumerate(time_slots):
            name = slot.get('name_kz' if lang == "KZ" else 'name_ru', slot.get('name_ru', ''))
            emoji = slot.get('emoji', '')
            time_range = slot.get('time_range_kz' if lang == "KZ" else 'time_range_ru', slot.get('time_range_ru', ''))
            
            # Убираем лишние пробелы
            name = name.strip()
            emoji = emoji.strip() if emoji else ''
            
            if time_range:
                option_text = format_choice_option(i, f"{emoji} {name} ({time_range})".strip())
            else:
                option_text = format_choice_option(i, f"{emoji} {name}".strip())
            time_options.append(option_text)
        await message.answer(t("training_time_question", lang), reply_markup=choices_keyboard(time_options, lang))
        return
    
    training_time = selected_time_slot.get('code', '')
    training_time_id = selected_time_slot.get('id')
    training_time_display = selected_time_slot.get('name_kz' if lang == "KZ" else 'name_ru', selected_time_slot.get('name_ru', ''))
    
    await send_event("training_time_selected", {"training_time": training_time, "training_time_id": training_time_id}, bot_user_id=message.from_user.id)
    await state.update_data(training_time=training_time, training_time_id=training_time_id, training_time_display=training_time_display)
    
    # Загружаем тарифы с учетом всех фильтров (category, format, time, gearbox)
    await _load_and_show_tariffs(message, state, lang, training_time_id=training_time_id)


@router.message(SchoolFlow.tariff)
async def schools_choose_tariff(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к выбору времени обучения
        data = await state.get_data()
        time_slots = data.get("training_time_slots", [])
        if time_slots:
            await state.set_state(SchoolFlow.training_time)
            time_options = []
            for i, slot in enumerate(time_slots):
                name = slot.get('name_kz' if lang == "KZ" else 'name_ru', slot.get('name_ru', ''))
                emoji = slot.get('emoji', '')
                time_range = slot.get('time_range_kz' if lang == "KZ" else 'time_range_ru', slot.get('time_range_ru', ''))
                
                # Убираем лишние пробелы
                name = name.strip()
                emoji = emoji.strip() if emoji else ''
                
                if time_range:
                    option_text = format_choice_option(i, f"{emoji} {name} ({time_range})".strip())
                else:
                    option_text = format_choice_option(i, f"{emoji} {name}".strip())
                time_options.append(option_text)
            await message.answer(t("training_time_question", lang), reply_markup=choices_keyboard(time_options, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    data = await state.get_data()
    tariffs = data.get("tariffs", [])
    # Ищем тариф по тексту сообщения
    selected_tariff = None
    text = message.text.strip()
    for tariff_item in tariffs:
        tariff_name = get_tariff_name(tariff_item, lang).strip()
        if text == tariff_name:
            selected_tariff = tariff_item
            break
    
    if not selected_tariff:
        opts = [format_choice_option(i, get_tariff_name(tariff_item, lang)) for i, tariff_item in enumerate(tariffs)]
        await message.answer(t("choose_tariff", lang), reply_markup=choices_keyboard(opts, lang))
        return
    tariff = selected_tariff
    await send_event("tariff_selected", {"tariff_name": tariff.get('name_ru') or tariff.get('name_kz', '')}, bot_user_id=message.from_user.id)
    await state.update_data(selected_tariff=tariff)
    
    # Получаем описание тарифа
    tariff_description = tariff.get('description_kz' if lang == "KZ" else 'description_ru', tariff.get('description_ru', ''))
    tariff_name = get_tariff_name(tariff, lang)
    tariff_price = tariff.get('price_kzt', 0)
    
    # Показываем описание тарифа, если оно есть, или цену, если описания нет
    if tariff_description:
        description_text = (
            f"<b>{tariff_name} — {tariff_price:,} ₸</b>\n\n"
            f"{tariff_description}"
        )
        await message.answer(description_text, parse_mode="HTML")
    else:
        # Если нет описания, показываем только цену
        price_text = f"<b>{tariff_name} — {tariff_price:,} ₸</b>"
        await message.answer(price_text, parse_mode="HTML")
    
    await send_event("lead_form_opened", {"step": "name", "flow": "schools"}, bot_user_id=message.from_user.id)
    await state.set_state(SchoolFlow.name)
    await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))


@router.message(SchoolFlow.name)
async def schools_enter_name(message: Message, state: FSMContext):
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
            await state.set_state(SchoolFlow.tariff)
            opts = [format_choice_option(i, get_tariff_name(tariff_item, lang)) for i, tariff_item in enumerate(tariffs)]
            await message.answer(t("choose_tariff", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(t("invalid_name", lang), reply_markup=back_keyboard(lang))
        return
    await state.update_data(name=name)
    await state.set_state(SchoolFlow.phone)
    await message.answer(t("enter_phone_contact", lang), reply_markup=phone_keyboard(lang))


@router.message(SchoolFlow.phone)
async def schools_enter_phone(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        # Возврат к вводу имени
        await state.set_state(SchoolFlow.name)
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
    detail = data["school_detail"]
    tariff = data["selected_tariff"]
    cities = data.get("cities", [])
    categories = data.get("categories", [])
    formats = data.get("formats", [])
    city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), str(data['city_id']))
    category_name = next((get_name_by_lang(c, lang) for c in categories if c["id"] == data['category_id']), str(data['category_id']))
    format_name = next((get_name_by_lang(f, lang) for f in formats if f["id"] == data['training_format_id']), str(data['training_format_id']))
    school_name = get_name_by_lang(detail.get('name', {}), lang) or detail.get('name', {}).get('ru', '')
    tariff_name = get_tariff_name(tariff, lang)
    
    # Получаем время обучения
    training_time_display = data.get('training_time_display', '')
    if not training_time_display:
        training_time = data.get('training_time', '')
        if training_time == "MORNING":
            training_time_display = t("training_time_morning", lang)
        elif training_time == "DAY":
            training_time_display = t("training_time_day", lang)
        elif training_time == "EVENING":
            training_time_display = t("training_time_evening", lang)
    
    # Получаем КПП из state или тарифа
    gearbox = data.get('gearbox') or tariff.get('gearbox')
    gearbox_text = ""
    if gearbox:
        if gearbox == "AT" or gearbox == "AUTOMATIC":
            gearbox_text = f" ({t('gearbox_automatic', lang)})"
        elif gearbox == "MT" or gearbox == "MANUAL":
            gearbox_text = f" ({t('gearbox_manual', lang)})"
    
    confirm_text_ru = (
        f"{t('confirm_data', lang)}\n\n"
        f"Город: {city_name}\n"
        f"Категория: {category_name}{gearbox_text}\n"
        f"{t('training_format_label', lang)}: {format_name}\n"
        f"{t('training_time_label', lang)}: {training_time_display}\n"
        f"Автошкола: {school_name}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {phone}"
    )
    confirm_text_kz = (
        f"{t('confirm_data', lang)}\n\n"
        f"Қала: {city_name}\n"
        f"Санат: {category_name}{gearbox_text}\n"
        f"{t('training_format_label', lang)}: {format_name}\n"
        f"{t('training_time_label', lang)}: {training_time_display}\n"
        f"Автошкола: {school_name}\n"
        f"Аты: {data['name']}\n"
        f"Телефон: {phone}"
    )
    text = confirm_text_kz if lang == "KZ" else confirm_text_ru
    await state.set_state(SchoolFlow.confirm)
    await message.answer(text, reply_markup=confirm_keyboard(lang))


@router.message(SchoolFlow.confirm, F.text.in_(["✅ Всё верно", "✅ Барлығы дұрыс"]))
async def schools_confirm(message: Message, state: FSMContext):
    lang = await get_language(state)
    data = await state.get_data()
    detail = data["school_detail"]
    tariff = data["selected_tariff"]
    api = ApiClient()
    gearbox = data.get('gearbox') or tariff.get('gearbox')
    payload = {
        "type": "SCHOOL",
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
            "category_id": data["category_id"],
            "training_format_id": data["training_format_id"],
            "training_time_id": data.get("training_time_id"),
            "school_id": data["school_id"],
            "tariff_name": tariff.get('name_ru') or tariff.get('name_kz', ''),
            "tariff_price_kzt": tariff.get("price_kzt"),
            "gearbox": gearbox,
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
    await send_event("lead_submitted", {"type": "SCHOOL"}, bot_user_id=message.from_user.id, lead_id=lead_id)
    
    # Получаем данные для WhatsApp сообщения
    categories = data.get("categories", [])
    category_name = ""
    for c in categories:
        if c.get("id") == data.get("category_id"):
            category_name = get_name_by_lang(c, lang)
            break
    
    formats = data.get("formats", [])
    format_name = next((get_name_by_lang(f, lang) for f in formats if f["id"] == data['training_format_id']), "")
    
    cities = data.get("cities", [])
    city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), "")
    
    training_time_code = data.get("training_time", "")
    # Получаем полное название времени обучения
    time_slots = data.get("training_time_slots", [])
    training_time_display_wa = ""
    for slot in time_slots:
        if slot.get('code') == training_time_code:
            training_time_display_wa = slot.get('name_kz' if lang == "KZ" else 'name_ru', slot.get('name_ru', ''))
            break
    
    gearbox = data.get('gearbox') or tariff.get("gearbox", "")
    
    # Показываем благодарность согласно ТЗ
    await message.answer(t("thank_you", lang), reply_markup=main_menu(lang))
    
    # Генерируем WhatsApp ссылку с шаблоном (автоматически открывается)
    wa_link = build_wa_link_school(
        detail, data["name"], data["phone"], tariff, category_name, lang,
        training_time=training_time_display_wa, training_format=format_name, city_name=city_name, gearbox=gearbox
    )
    if wa_link:
        await send_event("whatsapp_opened", {"flow": "schools", "school_id": data["school_id"]}, bot_user_id=message.from_user.id)
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


@router.message(SchoolFlow.confirm)
async def schools_confirm_any(message: Message, state: FSMContext):
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
        await state.set_state(SchoolFlow.name)
        await message.answer(t("enter_name", lang), reply_markup=back_keyboard(lang))
        return
    
    # Если не "Всё верно" и не "Исправить", показываем снова подтверждение
    data = await state.get_data()
    detail = data["school_detail"]
    tariff = data["selected_tariff"]
    cities = data.get("cities", [])
    categories = data.get("categories", [])
    formats = data.get("formats", [])
    city_name = next((get_name_by_lang(c, lang) for c in cities if c["id"] == data['city_id']), str(data['city_id']))
    category_name = next((get_name_by_lang(c, lang) for c in categories if c["id"] == data['category_id']), str(data['category_id']))
    format_name = next((get_name_by_lang(f, lang) for f in formats if f["id"] == data['training_format_id']), str(data['training_format_id']))
    school_name = get_name_by_lang(detail.get('name', {}), lang) or detail.get('name', {}).get('ru', '')
    tariff_name = get_tariff_name(tariff, lang)
    
    # Получаем время обучения
    training_time_display = data.get('training_time_display', '')
    if not training_time_display:
        training_time = data.get('training_time', '')
        if training_time == "MORNING":
            training_time_display = t("training_time_morning", lang)
        elif training_time == "DAY":
            training_time_display = t("training_time_day", lang)
        elif training_time == "EVENING":
            training_time_display = t("training_time_evening", lang)
    
    # Получаем КПП из тарифа, если есть
    gearbox_text = ""
    if tariff.get('gearbox'):
        if tariff['gearbox'] == "AUTOMATIC":
            gearbox_text = f" ({t('gearbox_automatic', lang)})"
        elif tariff['gearbox'] == "MANUAL":
            gearbox_text = f" ({t('gearbox_manual', lang)})"
    
    confirm_text_ru = (
        f"{t('confirm_data', lang)}\n\n"
        f"Город: {city_name}\n"
        f"Категория: {category_name}{gearbox_text}\n"
        f"{t('training_format_label', lang)}: {format_name}\n"
        f"{t('training_time_label', lang)}: {training_time_display}\n"
        f"Автошкола: {school_name}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}"
    )
    confirm_text_kz = (
        f"{t('confirm_data', lang)}\n\n"
        f"Қала: {city_name}\n"
        f"Санат: {category_name}{gearbox_text}\n"
        f"{t('training_format_label', lang)}: {format_name}\n"
        f"{t('training_time_label', lang)}: {training_time_display}\n"
        f"Автошкола: {school_name}\n"
        f"Аты: {data['name']}\n"
        f"Телефон: {data['phone']}"
    )
    text = confirm_text_kz if lang == "KZ" else confirm_text_ru
    await message.answer(text, reply_markup=confirm_keyboard(lang))

