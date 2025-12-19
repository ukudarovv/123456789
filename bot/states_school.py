from aiogram.fsm.state import State, StatesGroup


class SchoolFlow(StatesGroup):
    city = State()
    category = State()
    training_format = State()
    school = State()
    school_card = State()  # Показ карточки школы с кнопкой "Записаться"
    tariff = State()
    name = State()
    phone = State()
    confirm = State()

