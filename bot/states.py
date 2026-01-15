from aiogram.fsm.state import State, StatesGroup


class TestsFlow(StatesGroup):
    category = State()  # Выбор категории перед формой
    name = State()  # Имя и фамилия
    iin = State()  # ИИН
    phone = State()  # Телефон
    whatsapp = State()  # WhatsApp (request_contact)
    confirm = State()  # Подтверждение

