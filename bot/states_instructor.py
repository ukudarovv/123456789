from aiogram.fsm.state import State, StatesGroup


class InstructorFlow(StatesGroup):
    city = State()
    category = State()  # Добавлен выбор категории
    gearbox = State()
    instructor_gender = State()  # Обновлен: М/Ж/Не важно
    instructor = State()
    instructor_card = State()  # Показ карточки инструктора с кнопкой "Выбрать тариф"
    tariff = State()  # Выбор тарифа инструктора (если есть несколько)
    preferred_time = State()  # Удобное время занятий
    training_period = State()  # Предпочтительный период обучения
    name = State()
    phone = State()
    confirm = State()

