"""全局配置"""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 模型配置
TEXT_MODEL = os.getenv("TEXT_MODEL", "deepseek-chat")

# 视觉模型配置（用于截图识别，需要支持图片输入的多模态模型）
# 如果 VISION_API_KEY / VISION_BASE_URL 未设置，则复用 OPENAI 的配置
VISION_MODEL = os.getenv("VISION_MODEL", "deepseek-chat")
VISION_API_KEY = os.getenv("VISION_API_KEY", OPENAI_API_KEY)
VISION_BASE_URL = os.getenv("VISION_BASE_URL", OPENAI_BASE_URL)

# 推送配置
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")
WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
BARK_URL = os.getenv("BARK_URL", "")  # 例如 https://api.day.app/你的key
