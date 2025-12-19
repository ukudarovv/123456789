from aiogram.fsm.state import State, StatesGroup


class LanguageFlow(StatesGroup):
    select = State()

