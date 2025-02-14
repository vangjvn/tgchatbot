import logging
import aiohttp
from typing import Dict, Any
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import settings
# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# AI聊天配置
AI_CHAT_URL = "http://13.212.37.80:5087/api/v1/chat/xbt_agent_chat"


async def send_ai_request(user_id: str, user_name: str, question: str) -> Dict[Any, Any]:
    """
    发送请求到AI聊天服务
    """
    async with aiohttp.ClientSession() as session:
        payload = {
            "user_id": user_id,
            "user_name": user_name,
            "question": question
        }

        try:
            async with session.post(AI_CHAT_URL, json=payload) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"AI请求错误: {str(e)}")
            return {"answer": f"抱歉，服务出现错误: {str(e)}"}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理用户消息
    """
    if not update.message or not update.message.text:
        return

    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name

    # 检查是否是@机器人的消息
    bot_username = context.bot.username
    if f"@{bot_username}" in update.message.text:
        question = update.message.text.replace(f"@{bot_username}", "").strip()

        thinking_message = await update.message.reply_text("🤔 正在思考...")

        try:
            response = await send_ai_request(user_id, user_name, question)
            answer = response.get('answer', '抱歉，我没有得到答案')

            if response.get('msg_type') == 'image':
                if "|||||" in answer:
                    urls = answer.split("|||||")
                    for url in urls:
                        await update.message.reply_photo(photo=url)
                else:
                    await update.message.reply_photo(photo=answer)
            else:
                await update.message.reply_text(
                    text=answer,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            await update.message.reply_text(f"抱歉，发生错误: {str(e)}")
        finally:
            await thinking_message.delete()


def main() -> None:
    """
    主函数 - 使用同步方式启动机器人
    """
    # 创建应用
    application = Application.builder().token(settings.TG_BOT_TOKEN).build()

    # 注册消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 启动机器人
    logger.info("机器人正在启动...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()