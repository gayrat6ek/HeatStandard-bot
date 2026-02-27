import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://backend:8000/api/v1")  # Default to docker service name

# Admin ID for errors/notifications (optional)
ADMINS = os.getenv("ADMINS", "").split(",")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Admin group chat ID for order notifications
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "-1003559418523"))
