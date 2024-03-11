import argparse
import os
import asyncio
import requests

import nextcord
from nextcord.ext import commands

# Load environment variables
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
API_KEY = os.getenv("ANTHROPIC_API_KEY")
API_URL = "https://api.anthropic.com/v1/messages"


def call_anthropic_api(user_prompt: str) -> str:
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"  
    }
    payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    response_data = response.json()

    if response.status_code == 200:
        # Assuming the API's response format, adjust as needed based on actual response
        return ' '.join([block['text'] for block in response_data['content'] if block['type'] == 'text'])
    else:
        # Simplified error handling, consider more detailed handling based on API's error schema
        print(f"Error: {response_data.get('error', {}).get('message', 'Unknown error')}")
        return "Sorry, I encountered an error while processing your request."


def format_response_for_channel(response: str) -> list[str]:
    """
    Splits a response into multiple parts to adhere to Discord's char limit per message.

    This function takes a long string (response) and divides it into a list of strings,
    each not exceeding Discord's character limit for messages (1999 characters).
    It splits the response by newline characters and ensures no single part exceeds
    the limit.

    Parameters:
    - response (str): The original response string to be formatted.

    Returns:
    - list[str]: A list of strings, each representing a part of the original response
      that can be sent as separate Discord messages without exceeding the
      character limit.
    """
    char_limit = 1999  # Discord's character limit for messages
    responses = []  # List to store the formatted response parts
    current_response = ""  # String to store the current part of the response
    lines = response.split("\n")

    # Split the response by newline characters
    for line in lines:
        if len(current_response) + len(line) + 1 > char_limit:
            responses.append(current_response)
            current_response = ""
        else:
            current_response += line + "\n"

    # Add the last part of the response to the list
    if current_response:
        responses.append(current_response)
    return responses


def main() -> None:
    """
    Initializes and runs the Discord bot without requiring command line arguments
    for configuration. This version is adapted for use with the Anthropic API.
    """

    # pgintern = PgIntern(NETWORK, SUBGRAPH_ID)  # No longer needed

    intents = nextcord.Intents.default()
    intents.members = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    async def handle_command(message: nextcord.Message, user_prompt: str) -> None:
        """
        Handles commands received from users, indicating typing status before and after
        processing the command, and sending the processed response back to the user.

        Args:
            message (nextcord.Message): The message object from Discord.
            user_prompt (str): The user's message content as a string.
        """
        # Show "is typing" immediately after receiving a command
        async with message.channel.typing():
            # Generate the response
            response = call_anthropic_api(user_prompt)
            formatted_responses = format_response_for_channel(response)

        # Show "is typing" again right before sending the response
        async with message.channel.typing():
            await asyncio.sleep(1)  # Simulate typing right before replying

        # Send the response
        for formatted_response in formatted_responses:
            await message.reply(formatted_response, mention_author=False)

    @bot.event
    async def on_message(message: nextcord.Message) -> None:
        """
        Processes messages sent to the bot, checking for commands or mentions
        to trigger responses.

        Args:
            message (nextcord.Message): The message object from Discord.
        """
        if message.author == bot.user:
            return

        if message.reference and message.reference.resolved:
            ref_message = await message.channel.fetch_message(
                message.reference.message_id
            )
            if ref_message.author == bot.user:
                user_prompt = message.content.strip()
                await handle_command(message, user_prompt)
                return

        if bot.user.mentioned_in(message) and message.content.startswith(
            bot.user.mention
        ):
            user_prompt = message.content.replace(bot.user.mention, "", 1).strip()
            await handle_command(message, user_prompt)
            return

        await bot.process_commands(message)

    print("Starting bot...")
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
