from aiogram.fsm.state import StatesGroup, State

class RegisterState(StatesGroup):
    language = State()
    phone = State()
    waiting_approval = State()

class MenuState(StatesGroup):
    main = State()
    order = State()
    language = State()
    comment = State()

class OrderState(StatesGroup):
    group = State()      # Replaces category and subcategory - handles all group levels
    product = State()
    amount = State()
    cart = State()

