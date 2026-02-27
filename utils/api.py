import aiohttp
import logging
from typing import Optional, Dict, Any, List
from data.config import API_URL, ADMIN_USERNAME, ADMIN_PASSWORD
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Task-local storage for user token
_token_var: ContextVar[Optional[str]] = ContextVar("user_token", default=None)

class BackendAPI:
    def __init__(self):
        self.base_url = API_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self._admin_token: Optional[str] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def set_user_token(self, token: Optional[str]):
        """Set user token for the current context."""
        _token_var.set(token)

    async def admin_login(self) -> bool:
        """Login as admin to get management token."""
        try:
            session = await self.get_session()
            payload = {
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            }
            async with session.post(f"{self.base_url}/auth/login", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self._admin_token = data.get("access_token")
                    logger.info("Admin login successful")
                    return True
                logger.error(f"Admin login failed: {response.status} - {await response.text()}")
                return False
        except Exception as e:
            logger.error(f"Admin login error: {e}")
            return False

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Unified request handler with automatic authentication."""
        session = await self.get_session()
        url = f"{self.base_url}{path}"
        
        # Internal flag to prevent infinite recursion
        is_retry = kwargs.pop("_is_retry", False)
        
        headers = kwargs.get("headers", {})
        if "Authorization" not in headers:
            user_token = _token_var.get()
            token = user_token or self._admin_token
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        kwargs["headers"] = headers

        async with session.request(method, url, **kwargs) as response:
            if response.status == 401 and not is_retry:
                # Potential token expiry, try admin login again if we were using admin token
                if not _token_var.get() and await self.admin_login():
                    kwargs["_is_retry"] = True
                    # Update headers with new admin token
                    headers["Authorization"] = f"Bearer {self._admin_token}"
                    return await self._request(method, path, **kwargs)
                
            if response.status in [200, 201]:
                return await response.json()
            
            error_data = await response.text()
            logger.error(f"API Request Failed: {method} {path} - Status: {response.status} - Body: {error_data}")
            return {"error": f"Status {response.status}", "detail": error_data}

    async def register_user(self, telegram_id: str, phone_number: str, full_name: str, language: str) -> Dict[str, Any]:
        """Register a new user via Telegram."""
        payload = {
            "telegram_id": str(telegram_id),
            "phone_number": phone_number,
            "full_name": full_name,
            "current_lang": language
        }
        return await self._request("POST", "/auth/telegram/register", json=payload)

    async def login_user(self, telegram_id: str) -> Dict[str, Any]:
        """Login user via Telegram ID."""
        payload = {"telegram_id": str(telegram_id)}
        return await self._request("POST", "/auth/telegram/login", json=payload)

    async def get_user(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user details by Telegram ID. Uses admin token."""
        res = await self._request("GET", f"/users/telegram/{telegram_id}")
        if "error" in res:
            return None
        return res

    async def get_groups(self, parent_id: str = None) -> Dict[str, Any]:
        """Fetch groups."""
        path = "/groups?limit=100"
        path += f"&parent_id={parent_id if parent_id else 'null'}"
        return await self._request("GET", path)

    async def get_products(self, group_id: str) -> Dict[str, Any]:
        """Fetch products for a group."""
        return await self._request("GET", f"/products?group_id={group_id}&limit=100")

    async def search_products(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search products by name."""
        from urllib.parse import quote
        encoded_query = quote(query)
        return await self._request("GET", f"/products?search={encoded_query}&limit={limit}")
            
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get single product details."""
        res = await self._request("GET", f"/products/{product_id}")
        if "error" in res:
            return None
        return res

    async def create_order(self, order_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create a new order. User token should be in context."""
        # Ensure user_id is in payload
        order_data["user_id"] = user_id
        return await self._request("POST", "/orders", json=order_data)

    async def get_user_orders(self, user_id: str, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Fetch orders for a specific user."""
        return await self._request("GET", f"/orders?user_id={user_id}&skip={skip}&limit={limit}")

    async def update_lang(self, telegram_id: str, lang: str):
        """Update user language."""
        # Using /users/me/profile requires user token. 
        # If not in context, we login first.
        if not _token_var.get():
            login_res = await self.login_user(telegram_id)
            token = login_res.get("access_token")
            if token:
                self.set_user_token(token)
            else:
                return

        payload = {"current_lang": lang}
        await self._request("PUT", "/users/me/profile", json=payload)

    async def update_order_message_id(self, order_id: str, message_id: int):
        """Update order with telegram message ID."""
        payload = {"telegram_message_id": message_id}
        await self._request("PATCH", f"/orders/{order_id}", json=payload)

    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        """Update order status."""
        payload = {"status": status}
        return await self._request("PATCH", f"/orders/{order_id}", json=payload)

api_client = BackendAPI()
