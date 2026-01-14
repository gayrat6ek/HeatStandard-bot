import aiohttp
from typing import Optional, Dict, Any
from data.config import API_URL
import logging

logger = logging.getLogger(__name__)

class BackendAPI:
    def __init__(self):
        self.base_url = API_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def register_user(self, telegram_id: str, phone_number: str, full_name: str, language: str) -> Dict[str, Any]:
        """Register a new user via Telegram."""
        session = await self.get_session()
        payload = {
            "telegram_id": str(telegram_id),
            "phone_number": phone_number,
            "full_name": full_name,
            "current_lang": language
        }
        async with session.post(f"{self.base_url}/auth/telegram/register", json=payload) as response:
            if response.status == 201:
                return await response.json()
            error_data = await response.json()
            logger.error(f"Registration failed: {error_data}")
            return {"error": error_data.get("detail", "Registration failed")}

    async def login_user(self, telegram_id: str) -> Dict[str, Any]:
        """Login user via Telegram ID."""
        session = await self.get_session()
        payload = {"telegram_id": str(telegram_id)}
        async with session.post(f"{self.base_url}/auth/telegram/login", json=payload) as response:
            if response.status == 200:
                return await response.json()
            return {"error": "Login failed"}

    async def get_user(self, telegram_id: str) -> Dict[str, Any]:
        """Get user details by Telegram ID."""
        session = await self.get_session()
        # Using the specific endpoint for telegram lookup if available, or just rely on login to check existence?
        # The backend has /users/telegram/{telegram_id}
        async with session.get(f"{self.base_url}/users/telegram/{telegram_id}") as response:
            if response.status == 200:
                return await response.json()
            return None

    async def get_groups(self, parent_id: str = None) -> Dict[str, Any]:
        """Fetch groups. Use parent_id='null' for root groups, or a group id for children."""
        session = await self.get_session()
        if parent_id is None:
            # Get root groups
            url = f"{self.base_url}/groups?parent_id=null&limit=100"
        else:
            # Get child groups
            url = f"{self.base_url}/groups?parent_id={parent_id}&limit=100"
        
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return {"items": [], "total": 0}

    async def get_products(self, group_id: str) -> Dict[str, Any]:
        """Fetch products for a group."""
        session = await self.get_session()
        async with session.get(f"{self.base_url}/products?group_id={group_id}&limit=100") as response:
            if response.status == 200:
                return await response.json()
            return {"items": [], "total": 0}

    async def search_products(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search products by name."""
        from urllib.parse import quote
        session = await self.get_session()
        encoded_query = quote(query)
        url = f"{self.base_url}/products?search={encoded_query}&limit={limit}"
        logger.info(f"Searching products: {url}")
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"Search response: {len(data.get('items', []))} products found")
                return data
            logger.error(f"Search request failed: {response.status}")
            return {"items": [], "total": 0}
            
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get single product details."""
        session = await self.get_session()
        async with session.get(f"{self.base_url}/products/{product_id}") as response:
            if response.status == 200:
                return await response.json()
            return None

    async def create_order(self, order_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Create a new order."""
        session = await self.get_session()
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(f"{self.base_url}/orders", json=order_data, headers=headers) as response:
            if response.status == 201:
                return await response.json()
            error_text = await response.text()
            logger.error(f"Order creation failed: {error_text}")
            return {"error": "Order creation failed"}

    async def update_lang(self, telegram_id: str, lang: str):
        """Update user language."""
        # First login to get token (or search user by telegram id if endpoint allows open update which it shouldn't)
        # We need token to update info usually.
        # But wait, the menu handler doesn't have token in state if they just clicked settings without ordering?
        # The start handler logs them in.
        # Let's assume we can login with telegram_id to get token.
        login_res = await self.login_user(telegram_id)
        token = login_res.get("access_token")
        if not token:
            return
            
        session = await self.get_session()
        headers = {"Authorization": f"Bearer {token}"}
        
        # We need to call PUT /users/me/profile
        payload = {"current_lang": lang}
        async with session.put(f"{self.base_url}/users/me/profile", json=payload, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Failed to update language: {await response.text()}")

    async def update_order_message_id(self, order_id: str, message_id: int, token: str):
        """Update order with telegram message ID."""
        session = await self.get_session()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"telegram_message_id": message_id}
        async with session.patch(f"{self.base_url}/orders/{order_id}", json=payload, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Failed to update order message ID: {await response.text()}")

    async def update_order_status(self, order_id: str, status: str, token: str) -> Dict[str, Any]:
        """Update order status."""
        session = await self.get_session()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"status": status}
        async with session.patch(f"{self.base_url}/orders/{order_id}", json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            logger.error(f"Failed to update order status: {await response.text()}")
            return {"error": "Failed to update status"}

api_client = BackendAPI()
