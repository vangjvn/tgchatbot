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

    # 添加日志，查看接收到的消息
    logger.info(f"收到消息: {update.message.text}")
    logger.info(f"来自用户: {update.message.from_user.first_name} ({update.message.from_user.id})")
    logger.info(f"在群组: {update.message.chat.title} ({update.message.chat.id})")

    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name

    # 检查是否是@机器人的消息
    bot_username = context.bot.username
    logger.info(f"Bot username: {bot_username}")
    logger.info(f"update.message.text:{update.message.text}")
    logger.info(f"update.message.entities:{update.message.entities}")
    # 修改检测逻辑
    if update.message.text.startswith(f"@{bot_username}") or update.message.entities and any(
            entity.type == "mention" for entity in update.message.entities
    ):
        # 移除@部分，获取实际问题
        question = update.message.text.replace(f"@{bot_username}", "").strip()
        logger.info(f"处理问题: {question}")

        thinking_message = await update.message.reply_text("🤔 正在思考...")

        try:
            response = await send_ai_request(user_id, user_name, question)
            answer = response.get('answer', '抱歉，我没有得到答案')
            logger.info(f"AI回答: {answer}")

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
            logger.error(f"处理消息时发生错误: {str(e)}")
            await update.message.reply_text(f"抱歉，发生错误: {str(e)}")
        finally:
            await thinking_message.delete()


def main() -> None:
    """
    主函数
    """
    # 创建应用
    application = Application.builder().token(settings.TG_BOT_TOKEN).build()

    # 注册消息处理器
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    # 添加开始命令处理器
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("你好！我是ZAIXBT，在群组中@我即可开始对话。")

    application.add_handler(CommandHandler("start", start))

    # 启动机器人
    logger.info("机器人正在启动...")
    logger.info("等待消息中...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=1.0
    )


if __name__ == '__main__':
    main()