from aiogram.fsm.state import State, StatesGroup


class CertificateFlow(StatesGroup):
    """Состояния для потока 'Есть сертификат'"""
    select_action = State()  # Выбор действия: Тесты/Автошкола/Инструктор
    # Если выбраны тесты - переход в TestsFlow
    # Если выбрана автошкола - переход в SchoolFlow
    # Если выбран инструктор - переход в InstructorFlow

