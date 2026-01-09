from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import DEFAULT_LANGUAGE
from i18n import t
from keyboards.common import main_menu, back_keyboard, choices_keyboard, phone_keyboard, confirm_keyboard
from services.api import ApiClient, ApiClientError, ApiServerError, ApiTimeoutError, ApiNetworkError
from states import TestsFlow
from utils.validators import normalize_phone, is_valid_iin, is_valid_email
from utils.whatsapp import build_wa_link_tests
from services.analytics import send_event
from aiogram.types import ContentType

router = Router()


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


async def get_language(state: FSMContext) -> str:
    """Получить язык из state или вернуть дефолтный"""
    data = await state.get_data()
    return data.get("language", DEFAULT_LANGUAGE)


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


def is_back(text: str, lang: str = "RU") -> bool:
    if not text:
        return False
    text_lower = text.lower()
    if lang == "KZ":
        return text_lower in {t("back", "KZ").lower(), "назад"}
    return text_lower in {t("back", "RU").lower()}


def is_main_menu(text: str, lang: str = "RU") -> bool:
    if not text:
        return False
    text_lower = text.lower()
    if lang == "KZ":
        return text_lower in {t("main_menu", "KZ").lower(), "главное меню"}
    return text_lower in {t("main_menu", "RU").lower()}


# Обработчики кнопок меню должны быть первыми и работать в любом состоянии
@router.message(F.text.in_(["Главное меню", "Басты мәзір", "главное меню", "басты мәзір"]))
async def handle_main_menu(message: Message, state: FSMContext):
    lang = await get_language(state)
    await state.clear()
    await message.answer(t("main_welcome", lang), reply_markup=main_menu(lang))


@router.message(Command("tests"))
@router.message(F.text.in_(["Только тесты ПДД", "Тек ЖҚД тесттері", "только тесты пдд"]))
async def tests_start(message: Message, state: FSMContext):
    # Очищаем текущее состояние перед началом нового потока
    await state.clear()
    lang = await get_language(state)
    await send_event("flow_selected", {"flow": "tests"}, bot_user_id=message.from_user.id)
    api = ApiClient()
    try:
        settings = await api.get_settings()
        categories = await api.get_categories(for_tests=True)
    except Exception as e:
        await api.close()
        await handle_api_error(e, lang, message, state)
        return
    await api.close()
    
    if not categories:
        await message.answer(t("no_categories", lang) if hasattr(t, "no_categories") else "Категории не найдены", reply_markup=main_menu(lang))
        return
    
    price = settings.get("tests_price_kzt", 0)
    await state.update_data(settings=settings, categories=categories, language=lang)
    await state.set_state(TestsFlow.category)
    options = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(categories)]
    await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(options, lang))


@router.message(TestsFlow.category)
async def tests_choose_category(message: Message, state: FSMContext):
    """Обработка выбора категории для тестов"""
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    data = await state.get_data()
    categories = data.get("categories", [])
    selected_category = find_item_by_text(categories, message.text, lang)
    if not selected_category:
        opts = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(categories)]
        await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))
        return
    category_id = selected_category["id"]
    category_name = get_name_by_lang(selected_category, lang)
    
    await send_event("category_selected", {"category_id": category_id}, bot_user_id=message.from_user.id)
    await state.update_data(category_id=category_id, category_name=category_name)
    
    # Показываем информацию о тестах согласно ТЗ
    settings = data.get("settings", {})
    price = settings.get("tests_price_kzt", 0)
    
    info_text_ru = (
        f"{t('tests_info_title', lang)} «{category_name}»\n"
        f"{t('tests_info_price', lang)}: {price} KZT\n"
        f"{t('tests_info_format', lang)}"
    )
    info_text_kz = (
        f"{t('tests_info_title', lang)} «{category_name}»\n"
        f"{t('tests_info_price', lang)}: {price} KZT\n"
        f"{t('tests_info_format', lang)}"
    )
    info_text = info_text_kz if lang == "KZ" else info_text_ru
    
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    apply_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("tests_apply_button", lang))]],
        resize_keyboard=True,
    )
    
    await message.answer(info_text, reply_markup=apply_keyboard)
    # Ждем нажатия кнопки "Оставить заявку"
    await state.set_state(TestsFlow.name)


@router.message(TestsFlow.name)
async def tests_name(message: Message, state: FSMContext):
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
            await state.set_state(TestsFlow.category)
            opts = [format_choice_option(i, get_name_by_lang(c, lang)) for i, c in enumerate(categories)]
            await message.answer(t("choose_category", lang), reply_markup=choices_keyboard(opts, lang))
        else:
            await state.clear()
            await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    
    # Проверяем, нажата ли кнопка "Оставить заявку" (если еще не начали форму)
    apply_text_ru = t("tests_apply_button", "RU")
    apply_text_kz = t("tests_apply_button", "KZ")
    if message.text in [apply_text_ru, apply_text_kz]:
        # Нажата кнопка "Оставить заявку" - начинаем форму
        await send_event("register_button_clicked", {"flow": "tests"}, bot_user_id=message.from_user.id)
        await send_event("lead_form_opened", {"step": "name"}, bot_user_id=message.from_user.id)
        await message.answer(t("enter_name_full", lang), reply_markup=back_keyboard(lang))
        return
    
    # Ввод имени и фамилии
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(t("invalid_name", lang), reply_markup=back_keyboard(lang))
        return
    await state.update_data(name=name)
    await message.answer(t("enter_iin", lang), reply_markup=back_keyboard(lang))
    await state.set_state(TestsFlow.iin)


@router.message(TestsFlow.iin)
async def tests_iin(message: Message, state: FSMContext):
    lang = await get_language(state)
    iin = message.text.strip()
    if not is_valid_iin(iin):
        await message.answer(t("invalid_iin", lang), reply_markup=back_keyboard(lang))
        return
    await state.update_data(iin=iin)
    await message.answer(t("enter_whatsapp_contact", lang), reply_markup=phone_keyboard(lang))
    await state.set_state(TestsFlow.whatsapp)


@router.message(TestsFlow.whatsapp)
async def tests_whatsapp(message: Message, state: FSMContext):
    lang = await get_language(state)
    if is_main_menu(message.text, lang):
        await state.clear()
        await message.answer(t("main_menu", lang), reply_markup=main_menu(lang))
        return
    if is_back(message.text, lang):
        await state.set_state(TestsFlow.iin)
        await message.answer(t("enter_iin", lang), reply_markup=back_keyboard(lang))
        return
    
    # Обработка request_contact
    whatsapp = None
    if message.contact:
        whatsapp = normalize_phone(message.contact.phone_number)
    elif message.text:
        whatsapp = normalize_phone(message.text)
    
    if not whatsapp:
        await message.answer(t("invalid_phone", lang), reply_markup=phone_keyboard(lang))
        return
    
    await state.update_data(whatsapp=whatsapp)
    
    # Показываем экран подтверждения
    data = await state.get_data()
    category_name = data.get("category_name", "")
    
    confirm_text_ru = (
        f"{t('confirm_data', lang)}\n\n"
        f"👤 Имя, фамилия и отчество: {data['name']}\n"
        f"🆔 ИИН: {data['iin']}\n"
        f"💬 WhatsApp номер: {whatsapp}\n"
        f"📘 Услуга: {t('tests_info_title', lang)} {category_name}"
    )
    confirm_text_kz = (
        f"{t('confirm_data', lang)}\n\n"
        f"👤 Аты, тегі және әкесінің аты: {data['name']}\n"
        f"🆔 ЖСН: {data['iin']}\n"
        f"💬 WhatsApp нөмірі: {whatsapp}\n"
        f"📘 Қызмет: {t('tests_info_title', lang)} {category_name}"
    )
    text = confirm_text_kz if lang == "KZ" else confirm_text_ru
    await message.answer(text, reply_markup=confirm_keyboard(lang))
    await state.set_state(TestsFlow.confirm)


@router.message(TestsFlow.confirm, F.text.in_(["✅ Всё верно", "✅ Барлығы дұрыс"]))
async def tests_confirm(message: Message, state: FSMContext):
    lang = await get_language(state)
    data = await state.get_data()
    category_name = data.get("category_name", "")
    
    api = ApiClient()
    payload = {
        "type": "TESTS",
        "language": lang,
        "bot_user": {
            "telegram_user_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language": lang,
        },
        "contact": {"name": data["name"], "phone": data["whatsapp"]},
        "payload": {
            "category_id": data.get("category_id"),
            "iin": data["iin"],
            "whatsapp": data["whatsapp"],
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
    await send_event("lead_submitted", {"type": "TESTS"}, bot_user_id=message.from_user.id, lead_id=lead_id)
    
    # Показываем благодарность согласно ТЗ
    await message.answer(t("thank_you", lang), reply_markup=main_menu(lang))
    
    # Генерируем WhatsApp сообщение владельцу согласно ТЗ
    # Получаем номер WhatsApp из настроек
    settings = data.get("settings", {})
    owner_whatsapp = settings.get("owner_whatsapp", "")
    wa_link = build_wa_link_tests("", data, category_name, lang, owner_whatsapp=owner_whatsapp)
    if wa_link:
        await send_event("whatsapp_opened", {"flow": "tests"}, bot_user_id=message.from_user.id)
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


@router.message(TestsFlow.confirm)
async def tests_confirm_any(message: Message, state: FSMContext):
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
        await state.set_state(TestsFlow.name)
        await message.answer(t("enter_name_full", lang), reply_markup=back_keyboard(lang))
        return
    
    # Если не "Всё верно" и не "Исправить", показываем снова подтверждение
    data = await state.get_data()
    category_name = data.get("category_name", "")
    
    confirm_text_ru = (
        f"{t('confirm_data', lang)}\n\n"
        f"👤 Имя, фамилия и отчество: {data['name']}\n"
        f"🆔 ИИН: {data['iin']}\n"
        f"💬 WhatsApp номер: {data['whatsapp']}\n"
        f"📘 Услуга: {t('tests_info_title', lang)} {category_name}"
    )
    confirm_text_kz = (
        f"{t('confirm_data', lang)}\n\n"
        f"👤 Аты, тегі және әкесінің аты: {data['name']}\n"
        f"🆔 ЖСН: {data['iin']}\n"
        f"💬 WhatsApp нөмірі: {data['whatsapp']}\n"
        f"📘 Қызмет: {t('tests_info_title', lang)} {category_name}"
    )
    text = confirm_text_kz if lang == "KZ" else confirm_text_ru
    await message.answer(text, reply_markup=confirm_keyboard(lang))

