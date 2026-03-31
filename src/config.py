"""全局配置"""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 模型配置
TEXT_MODEL = "deepseek-chat"
VISION_MODEL = "deepseek-chat"  # 后期截图识别可换多模态模型

# 推送配置
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")
WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
