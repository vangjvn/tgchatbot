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

    # 添加更详细的日志
    logger.info(f"收到消息: {update.message.text}")
    logger.info(f"来自用户: {update.message.from_user.first_name} ({update.message.from_user.id})")
    logger.info(f"在聊天: {update.message.chat.type} ({update.message.chat.id})")

    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name
    bot_username = context.bot.username

    # 处理所有消息类型
    should_respond = False
    question = ""

    # 私聊消息直接回复
    if update.message.chat.type == 'private':
        should_respond = True
        question = update.message.text
        logger.info("私聊消息，直接回复")
    # 群聊消息需要@
    elif update.message.chat.type in ['group', 'supergroup']:
        if f"@{bot_username}" in update.message.text:
            should_respond = True
            question = update.message.text.replace(f"@{bot_username}", "").strip()
            logger.info("群聊@消息，准备回复")

    if should_respond:
        logger.info(f"准备回答问题: {question}")
        try:
            # 发送"正在思考"消息
            thinking_message = await update.message.reply_text("🤔 正在思考...")

            # 调用 AI 服务
            logger.info(f"开始调用AI服务，参数：user_id={user_id}, user_name={user_name}, question={question}")
            response = await send_ai_request(user_id, user_name, question)
            logger.info(f"AI服务返回：{response}")

            answer = response.get('answer', '抱歉，我没有得到答案')

            # 判断回复类型并发送
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

            logger.info("回复发送成功")

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
        await update.message.reply_text("你好！我是ZAIXBT_bot，在群组中@我即可开始对话。")

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