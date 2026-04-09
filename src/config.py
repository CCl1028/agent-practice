"""全局配置"""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 模型配置
TEXT_MODEL = os.getenv("TEXT_MODEL", "deepseek-chat")

# 视觉模型配置（用于截图识别，需要支持图片输入的多模态模型）
# 默认使用硅基流动的 Qwen-VL（便宜且支持中文图片识别）
VISION_MODEL = os.getenv("VISION_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
VISION_API_KEY = os.getenv("VISION_API_KEY") or OPENAI_API_KEY
VISION_BASE_URL = os.getenv("VISION_BASE_URL", "https://api.siliconflow.cn/v1")

# 推送配置
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")
WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
BARK_URL = os.getenv("BARK_URL", "")  # 例如 https://api.day.app/你的key

# --- v2 新增：新闻搜索配置（4 引擎，配置任一即可） ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")     # 推荐，免费 1000 次/月
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")        # 中文搜索优化
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")        # 隐私优先，海外优化
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")     # Google 搜索兜底
