from aiogram.fsm.state import State, StatesGroup


class SchoolFlow(StatesGroup):
    city = State()
    category = State()
    training_format = State()
    gearbox = State()  # Выбор КПП (Автомат/Механика)
    school = State()
    school_card = State()  # Показ карточки школы с кнопкой "Записаться"
    training_time = State()  # Выбор времени обучения (утро/день/вечер)
    tariff = State()
    name = State()
    phone = State()
    confirm = State()

