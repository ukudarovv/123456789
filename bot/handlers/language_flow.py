from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from i18n import t
from keyboards.common import main_menu, language_keyboard
from services.analytics import send_event
from states_language import LanguageFlow

router = Router()


@router.message(LanguageFlow.select)
async def language_selected(message: Message, state: FSMContext):
    text = message.text or ""
    lang = "KZ" if "қазақ" in text.lower() or "қаз" in text.lower() or "Қазақша" in text else "RU"
    
    # Отслеживаем выбор языка
    await send_event("language_selected", {"language": lang}, bot_user_id=message.from_user.id)
    
    # Сохраняем язык в state (будет использован при создании лида)
    await state.update_data(language=lang)
    await state.clear()
    
    await message.answer(
        t("main_welcome", lang),
        reply_markup=main_menu(lang),
    )

