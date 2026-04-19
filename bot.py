from dotenv import load_dotenv
import discord
import os
import re
import base64
from openai import OpenAI
from datetime import datetime, timezone, timedelta
from discord.ext import commands

load_dotenv()

client_ai = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

intents = discord.Intents.default()
intents.message_content = True

channels = [782032130837970954,1071911710664953928,1081217657199673426,1071519598781927438]
channels_not = [748230154819600434,782032135863009320,688065197881163799,689561034842832978,1272196983804919900]
banned = []

client = commands.Bot(command_prefix=".", intents=intents)

model = "meta-llama/llama-4-scout-17b-16e-instruct"

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await client.tree.sync()

@client.event
async def on_message(message):
    if message.author == client.user or message.author in banned or message.content == "<>" or message.author.bot:
        return

    if message.content.startswith("~") and message.author.id == 753730641996152862:
        id = message.content[1:message.content[1:].find("~")+1]
        text = message.content[message.content[1:].find("~")+2:]
        channel = client.get_channel(int(id))
        await channel.send(text)

    if message.content.startswith("!clear") and message.author.id == 753730641996152862:
        parts = message.content.split()
        if len(parts) > 1 and parts[1].isdigit():
            amount = int(parts[1])
            await message.channel.purge(limit=amount + 1)
        else:
            await message.channel.purge(limit=1)

    def filter_timed(messgae):
        if len(messgae.content) > 0 or len(messgae.attachments) > 0:
            if datetime.now(timezone.utc) - messgae.created_at <= timedelta(minutes=30) and messgae.content.find(".gif") == -1 and messgae.content.find("tenor") == -1:
                return True
        return False

    def filter_history(messgae):
        if len(messgae.content) > 0 or len(messgae.attachments) > 0:
            return True
        return False

    if message.channel.id in channels_not and client.user not in message.mentions:
        return

    if client.user not in message.mentions:
        return

    async with message.channel.typing():
        history = [msg async for msg in message.channel.history(limit=30)]
        history = list(filter(filter_history, history[0:3])) + list(filter(filter_timed, history[3:]))
        history.reverse()

        wipe = 0
        for i in range(len(history)):
            if history[i].content.find("<>") != -1:
                wipe = i + 1

        history = history[wipe:]

        try:
            sys_prompt = open("prompt.txt", "r").read()
        except Exception as e:
            print(f"Failed to load prompt: {e}")
            sys_prompt = "you are a glorp entity. you only speak in glorp."

        messages = [
            {"role": "system", "content": sys_prompt},
        ]

        for i in history:
            content_list = []

            text_val = i.clean_content if i.author == client.user else f"{i.author}: {i.clean_content.replace('<@1495228712986218517>', '@glorp')}"

            if text_val.strip():
                content_list.append({"type": "text", "text": text_val})

            for attachment in i.attachments:
                if attachment.content_type and attachment.content_type.startswith("image"):
                    image_data = await attachment.read()
                    base64_image = base64.b64encode(image_data).decode("utf-8")
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{attachment.content_type};base64,{base64_image}"}
                    })

            if not content_list:
                content_list.append({"type": "text", "text": "[Empty Message]"})

            messages.append({
                "role": "assistant" if i.author == client.user else "user",
                "content": content_list if len(content_list) > 1 else content_list[0]["text"]
            })

        for i in messages:
            print(i["role"], "(multimodal)" if isinstance(i["content"], list) else i["content"])

        print(f"{message.author}: {message.content}")

        try:
            response_obj = client_ai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=1.4,
                top_p=0.9,
                frequency_penalty=0.8,
            )
            response = response_obj.choices[0].message.content

            reply = response[:2000].replace("im_end>", "")
            reply = re.sub(r'\*[^*]*\*', '', reply)  # strip *actions*
            reply = re.sub(' +', ' ', reply)
            reply = re.sub(r'\n\s*\n', '\n\n', reply)
            reply = reply.strip()

            print(reply)
            await message.reply(reply, mention_author=True)

        except Exception as e:
            print(f"API Error: {e}")
            await message.reply("glorp...", mention_author=False)

client.run(os.getenv('TOKEN'))
