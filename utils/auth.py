from aiogram import BaseMiddleware, types
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable
from utils.api import api_client

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        state: FSMContext = data.get("state")
        if state:
            state_data = await state.get_data()
            token = state_data.get("token")
            api_client.set_user_token(token)
        
        return await handler(event, data)
