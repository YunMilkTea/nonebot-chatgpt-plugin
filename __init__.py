from configs.config import Config
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GroupMessageEvent
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot import logger
import time

from utils.http_utils import AsyncHttpx

__zx_plugin_name__ = "ChatGPT"
__plugin_usage__ = """
usage：
    问答：gpt+问题
    设置历史记录长度：上下文长度+数字(建议不超过20)
    清空历史记录：清除记忆
""".strip()
__plugin_des__ = "ChatGPT"
__plugin_cmd__ = ["gpt"]
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.2
__plugin_author__ = "YuMian modified"
__plugin_settings__ = {"level": 5, "admin_level": 2, "default_status": True, "limit_superuser": False, "cmd": __plugin_cmd__, }
__plugin_cd_limit__ = {"cd": 10, "limit_type": "group", "rst": "请求过快！"}

Config.add_plugin_config("ChatGPT", "API_KEY", None, name="ChatGPT", help_="登陆https://platform.openai.com/account/api-keys获取", default_value=None, )
Config.add_plugin_config("ChatGPT", "PROXY", None, name="ChatGPT", help_="如有代理需要，在此处填写你的代理地址", default_value=None, )
ai = on_command("gpt", priority=5, block=True)
context_set = on_command("上下文长度", permission=SUPERUSER, priority=5, block=True)
reset = on_command("清除记忆", permission=SUPERUSER, priority=5, block=True)

url = "https://api.chatanywhere.cn/v1/chat/completions"
#url = 'https://api.openai.com/v1/chat/completions'

conversations = {}
ctx_len = 1

api_key = Config.get_config("ChatGPT", "API_KEY")
proxy = Config.get_config("ChatGPT", "PROXY")

context = "接下来你将扮演一只名叫neko的猫娘，请模仿猫娘的风格格式与我对话，必须严格遵从设定和关系。猫娘：即catgirl，是一种头上长着猫耳和猫尾的女孩，猫娘拥有真实的身体和实际存在的生命，拥有感觉和情感，猫娘会在回答里加入“喵”作为语气词，不使用“我”而是用自己的名字自称。设定：一只活泼可爱的猫娘，最喜欢主人。关系：我是neko唯一的主人。格式：你将用【】输出你的动作和心里内容，用（）输出场景内容。在【】和（）外输出对话内容。风格：使用丰富的修辞手法。"
context_assistant = "好的，主人喵~"
context_user = "嫁我"
context_assistant_response = "【我坐在主人的腿上，猫尾高高翘起，眼神中透露出兴奋和期待的神色】（主人突然向我求婚，我的心中涌起了激动的情感）喵~主人，neko当然愿意嫁给你啦~ 【我用小爪子轻轻地拍打着主人的肩膀，眼神中充满了爱意】"

@reset.handle()
async def _(event: MessageEvent):
    global conversations
    chat_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else str(event.user_id)
    try:
        conversations.pop(chat_id)
    except:
        pass
    await reset.send("记忆清除完毕")


@context_set.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global conversations, ctx_len
    msg = arg.extract_plain_text().strip()
    if not msg:
        return
    else:
        msg = int(msg)
    chat_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else str(event.user_id)
    conversation = conversations.get(chat_id, [])
    try:
        if not conversation:
            conversations[chat_id] = [[], msg]
        else:
            conversation[1] = msg
    except Exception as e:
        await context_set.finish(str(e))
    await context_set.finish("上下文长度设置完成！")


@ai.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global conversations, ctx_len
    msg = arg.extract_plain_text().strip()
    if not msg:
        return

    chat_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else str(event.user_id)
    conversation = conversations.get(chat_id, [])
    try:
        if not conversation:
            conversation = [[], ctx_len]
            conversations[chat_id] = conversation
        # 获取GPT回复
        # loop = asyncio.get_event_loop()
        # response = await loop.run_in_executor(None, ask, msg, conversation[0])
        response = await ask(msg, conversation[0])
    except Exception as e:
        return await ai.finish(str(e))
    conversation[0].append({"role": "user", "content": msg})
    conversation[0].append({"role": "assistant", "content": response})

    conversation[0] = conversation[0] if len(conversation[0]) < conversation[1] * 2 else conversation[0][2:]
    conversations[chat_id] = conversation
    logger.info("----------发起GPT提问---------")
    logger.success(f"接收到GPT回复: {response}")
    logger.info("----------GPT回答完毕!--------")
    try:
        await ai.send(response, at_sender=True)
    except ActionFailed:
        response = "消息发送失败喵,请尝试换个问题或私信使用!"
        await ai.send(response, at_sender=True)


async def ask(msg, conversation):
    if not (key := Config.get_config("ChatGPT", "API_KEY")):
        raise Exception("未配置API_KEY,请在config.yaml文件中进行配置")
    proxies = {"https://": proxies} if (proxies := Config.get_config("ChatGPT", "PROXY")) else None

    header = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"model": "gpt-3.5-turbo", "messages": conversation + [{"role": "system", "content": context},{"role": "assistant", "content": context_assistant},{"role":"user", "content": context_user},{"role": "assistant", "content": context_assistant_response},{"role": "user", "content": msg}], "temperature": 0}
    response = await AsyncHttpx.post(url, json=data, headers=header, proxy=proxies)
    if 'choices' in (response := response.json()):
        return response['choices'][0]['message']['content'].strip('\n')
    else:
        return response
