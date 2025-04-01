import logging
import aiohttp
from typing import Dict, Any
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import settings

# 配置更详细的日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # 改为 DEBUG 级别
)
logger = logging.getLogger(__name__)

# 添加 telegram 相关的日志
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.DEBUG)

# AI聊天配置
AI_CHAT_URL = settings.AI_CHAT_URL


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
            logger.info(f"发送AI请求: {payload}")
            async with session.post(AI_CHAT_URL, json=payload) as response:
                result = await response.json()
                logger.info(f"AI响应: {result}")
                return result
        except Exception as e:
            logger.error(f"AI请求错误: {str(e)}")
            return {"answer": f"抱歉，服务出现错误: {str(e)}"}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理用户消息
    """
    # 首先记录收到的所有信息
    logger.debug("收到更新对象：%s", update)

    if update.message:
        logger.info("Raw message data: %s", update.message.to_dict())

    # 检查是否是机器人自己的消息，如果是则直接返回
    if update.message.from_user.is_bot:
        logger.info("忽略机器人自己的消息")
        return

    if not update.message or not update.message.text:
        logger.info("消息为空或不是文本消息")
        return

    # 记录基本信息
    logger.info(f"收到消息: {update.message.text}")
    logger.info(f"来自用户: {update.message.from_user.first_name} ({update.message.from_user.id})")
    logger.info(f"聊天类型: {update.message.chat.type}")
    logger.info(f"聊天ID: {update.message.chat.id}")
    if update.message.chat.title:
        logger.info(f"群组标题: {update.message.chat.title}")

    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name
    bot_username = context.bot.username

    logger.info(f"Bot username: {bot_username}")
    logger.info(f"消息文本: {update.message.text}")
    logger.info(f"消息实体: {update.message.entities}")

    # 检查是否需要回复
    should_reply = False
    question = ""

    # 私聊直接回复
    if update.message.chat.type == 'private':
        should_reply = True
        question = update.message.text
        logger.info("私聊消息，将回复")

    # 群聊检查@，优化检测逻辑
    elif update.message.chat.type in ['group', 'supergroup']:
        # 检查消息开头是否@机器人
        if update.message.text.startswith(f"@{bot_username}"):
            should_reply = True
            # 只去除开头的@mention
            question = update.message.text[len(f"@{bot_username}"):].strip()
            logger.info(f"群聊@消息，将回复问题: {question}")
        # 检查实体中是否有@机器人，且@在消息开头
        elif update.message.entities:
            for entity in update.message.entities:
                if (entity.type == "mention" and
                    entity.offset == 0 and
                    update.message.text[entity.offset:entity.offset+entity.length] == f"@{bot_username}"):
                    should_reply = True
                    question = update.message.text[entity.length:].strip()
                    logger.info(f"检测到mention实体，将回复问题: {question}")
                    break

    if should_reply:
        try:
            # 发送"正在思考"消息的英文版
            thinking_message = await update.message.reply_text("🤔 Thinking...")

            # 调用 AI 服务
            logger.info(f"准备调用AI服务: user_id={user_id}, user_name={user_name}, question={question}")
            response = await send_ai_request(user_id, user_name, question)
            logger.info(f"AI服务返回: {response}")

            # 输出英文的抱歉，我没有得到答案
            answer = response.get('answer', 'Sorry, I did not get an answer.')

            # 判断回复类型并发送
            if response.get('msg_type') == 'image':
                if "|||||" in answer:
                    urls = answer.split("|||||")
                    for url in urls:
                        await update.message.reply_photo(photo=url)
                else:
                    await update.message.reply_photo(photo=answer)
            else:
                await update.message.reply_text(text=answer)

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

    # 注册消息处理器 - 修改过滤条件
    application.add_handler(MessageHandler(
        filters.ALL,  # 改为接收所有消息
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
        poll_interval=1.0,
        timeout=30
    )


if __name__ == '__main__':
    main()