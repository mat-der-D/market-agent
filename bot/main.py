import os
import logging
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

import aiohttp
import discord
from discord import app_commands

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
API_URL = os.environ["API_URL"].rstrip("/")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-agent-bot")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

http_session: aiohttp.ClientSession | None = None


@client.event
async def on_ready():
    global http_session
    http_session = aiohttp.ClientSession()
    await tree.sync()
    logger.info("Logged in as %s (ID: %s)", client.user, client.user.id)


@client.event
async def on_close():
    if http_session and not http_session.closed:
        await http_session.close()


async def call_convert_api(from_currency: str, to_currency: str, amount: float) -> dict:
    payload = {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
    }
    async with http_session.post(
        f"{API_URL}/convert",
        json=payload,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        return await resp.json()


def format_success(amount: float, from_currency: str, to_currency: str, data: dict) -> str:
    result = data["result"]
    rate = data["rate"]
    fetched_at = data["fetched_at"]
    dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    dt_str = dt.astimezone(JST).strftime("%Y-%m-%d %H:%M")
    result_formatted = f"{result:,.2f}"
    amount_formatted = f"{amount:,g}"
    return (
        f"{amount_formatted} {from_currency} = {result_formatted} {to_currency}\n"
        f"（レート: {rate}、取得時刻: {dt_str} JST）"
    )


@tree.command(name="usd2jpy", description="USD を JPY に換算します")
@app_commands.describe(amount="換算する USD の金額")
async def usd2jpy(interaction: discord.Interaction, amount: float):
    await interaction.response.defer()
    try:
        data = await call_convert_api("USD", "JPY", amount)
        if data.get("error"):
            message = f"エラー: {data['error']}"
        else:
            message = format_success(amount, "USD", "JPY", data)
    except Exception:
        logger.exception("Error calling convert API")
        message = "エラー: API の呼び出しに失敗しました"
    await interaction.followup.send(message)


@tree.command(name="jpy2usd", description="JPY を USD に換算します")
@app_commands.describe(amount="換算する JPY の金額")
async def jpy2usd(interaction: discord.Interaction, amount: float):
    await interaction.response.defer()
    try:
        data = await call_convert_api("JPY", "USD", amount)
        if data.get("error"):
            message = f"エラー: {data['error']}"
        else:
            message = format_success(amount, "JPY", "USD", data)
    except Exception:
        logger.exception("Error calling convert API")
        message = "エラー: API の呼び出しに失敗しました"
    await interaction.followup.send(message)


client.run(DISCORD_TOKEN)
