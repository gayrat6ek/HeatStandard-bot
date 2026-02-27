"""
Admin handlers for order management via callback buttons.
Handles Accept/Decline buttons from admin group.
"""

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from utils.api import api_client
from data.config import ADMIN_GROUP_ID
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("order_accept:"))
async def accept_order(callback: types.CallbackQuery):
    """Handle order acceptance by admin."""
    order_id = callback.data.split(":")[1]
    
    try:
        # Update order status to confirmed.
        # This will use current user token if available, or fall back to admin token.
        res = await api_client.update_order_status(order_id, "confirmed")
        
        if "error" not in res:
            order_number = res.get("order_number", "N/A")
            
            # Edit the message to show it's confirmed
            new_text = callback.message.text.replace(
                "🕐 Ожидает подтверждения",
                f"✅ Подтверждено\n👤 Подтвердил: {callback.from_user.full_name}"
            )
            new_text = new_text.replace("🆕", "✅")
            
            await callback.message.edit_text(
                new_text,
                parse_mode="HTML",
                reply_markup=None  # Remove buttons
            )
            
            await callback.answer(f"Заказ #{order_number} подтвержден!")
            logger.info(f"Order {order_id} confirmed by {callback.from_user.id}")
        else:
            await callback.answer("Ошибка при подтверждении заказа", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error accepting order: {e}")
        await callback.answer("Ошибка при подтверждении заказа", show_alert=True)


@router.callback_query(F.data.startswith("order_decline:"))
async def decline_order(callback: types.CallbackQuery):
    """Handle order decline by admin."""
    order_id = callback.data.split(":")[1]
    
    try:
        # Update order status to declined
        res = await api_client.update_order_status(order_id, "declined")
        
        if "error" not in res:
            order_number = res.get("order_number", "N/A")
            
            # Edit the message to show it's declined
            new_text = callback.message.text.replace(
                "🕐 Ожидает подтверждения",
                f"❌ Отклонено\n👤 Отклонил: {callback.from_user.full_name}"
            )
            new_text = new_text.replace("🆕", "❌")
            
            await callback.message.edit_text(
                new_text,
                parse_mode="HTML",
                reply_markup=None  # Remove buttons
            )
            
            await callback.answer(f"Заказ #{order_number} отклонен!")
            logger.info(f"Order {order_id} declined by {callback.from_user.id}")
        else:
            await callback.answer("Ошибка при отклонении заказа", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error declining order: {e}")
        await callback.answer("Ошибка при отклонении заказа", show_alert=True)
