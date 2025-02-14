import logging
import aiohttp
from aiohttp_socks import ProxyConnector
from typing import Dict, Any
from telegram import Update
from telegram.constants import ParseMode  # ParseMode 移动到了 constants 模块
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes  # 新的导入方式
from telegram.request import HTTPXRequest  # 修正导入路径
from httpx import Proxy
import traceback
from config import settings

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # 改为 DEBUG 级别以获取更多信息
)
logger = logging.getLogger(__name__)

# 添加 httpx 的日志
logging.getLogger("httpx").setLevel(logging.DEBUG)
# 添加 telegram 的日志
logging.getLogger("telegram").setLevel(logging.DEBUG)
# AI聊天配置
AI_CHAT_URL = "http://13.212.37.80:5087/api/v1/chat/xbt_agent_chat"


async def send_ai_request(user_id: str, user_name: str, question: str) -> Dict[Any, Any]:
    """
    发送请求到AI聊天服务
    """
    connector = ProxyConnector.from_url(settings.PROXY_URL) if settings.IS_USE_PROXY else None

    async with aiohttp.ClientSession(connector=connector,
                                   timeout=aiohttp.ClientTimeout(total=60)) as session:
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
    # 只处理文本消息
    if not update.message or not update.message.text:
        return

    # 获取用户信息
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name

    # 检查是否是@机器人的消息
    bot_username = context.bot.username
    if f"@{bot_username}" in update.message.text:
        # 移除@部分，获取实际问题
        question = update.message.text.replace(f"@{bot_username}", "").strip()

        # 发送"正在思考"消息
        thinking_message = await update.message.reply_text(
            text="🤔 正在思考..."
        )

        try:
            # 调用AI服务
            response = await send_ai_request(user_id, user_name, question)
            answer = response.get('answer', '抱歉，我没有得到答案')

            # 判断是否是图片回复
            if response.get('msg_type') == 'image':
                if "|||||" in answer:
                    # 处理多张图片
                    urls = answer.split("|||||")
                    for url in urls:
                        await update.message.reply_photo(
                            photo=url
                        )
                else:
                    # 发送单张图片
                    await update.message.reply_photo(
                        photo=answer
                    )
            else:
                # 发送文本回复
                await update.message.reply_text(
                    text=answer,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            await update.message.reply_text(
                text=f"抱歉，发生错误: {str(e)}"
            )
        finally:
            # 删除"正在思考"消息
            await thinking_message.delete()


async def main() -> None:
    """
    主函数
    """
    try:
        logger.debug(f"使用代理设置: IS_USE_PROXY={settings.IS_USE_PROXY}, PROXY_URL={settings.PROXY_URL}")

        if settings.IS_USE_PROXY:
            proxy = Proxy(url=settings.PROXY_URL)
            logger.debug(f"创建代理对象: {proxy}")

            # 修改这部分代码
            request = HTTPXRequest(proxy=proxy)
            application = (
                Application.builder()
                .token(settings.TG_BOT_TOKEN)
                .http_version("1.1")
                .get_updates_request(request)
                .connect_timeout(30.0)  # 使用 builder 方法设置超时
                .read_timeout(30.0)
                .write_timeout(30.0)
                .build()
            )
            logger.debug("使用代理创建应用完成")
        else:
            application = Application.builder().token(settings.TG_BOT_TOKEN).build()
            logger.debug("创建无代理应用完成")

        # 注册消息处理器
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        ))
        logger.debug("消息处理器注册完成")

        # 启动机器人
        logger.info("机器人正在启动...")

        # 测试网络连接
        async with aiohttp.ClientSession() as session:
            try:
                logger.debug("测试到 Telegram API 的连接...")
                async with session.get(
                        "https://api.telegram.org",
                        proxy=settings.PROXY_URL if settings.IS_USE_PROXY else None,
                        timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    logger.debug(f"Telegram API 测试响应: {response.status}")
            except Exception as e:
                logger.error(f"连接测试失败: {str(e)}")

        logger.debug("开始初始化应用...")
        await application.initialize()
        logger.debug("应用初始化完成")

        logger.debug("开始启动应用...")
        await application.start()
        logger.debug("应用启动完成")

        logger.debug("开始轮询更新...")
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0  # 添加轮询间隔
        )
        logger.info("机器人已启动...")

    except Exception as e:
        logger.error(f"启动过程中发生错误: {str(e)}")
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise


if __name__ == '__main__':
    try:
        import asyncio

        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("机器人被用户停止")
    except Exception as e:
        logger.error(f"机器人因错误停止: {str(e)}")
        logger.error(f"详细错误信息: {traceback.format_exc()}")