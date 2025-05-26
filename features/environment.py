import os
import asyncio
from unittest.mock import patch


def before_all(context):
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)


def after_all(context):
    context.loop.close()


def before_scenario(context, scenario):
    os.environ["OBSIDIAN_API_URL"] = "https://localhost:27124"
    os.environ["OBSIDIAN_API_KEY"] = "test-api-key"


def after_scenario(context, scenario):
    for key in ["OBSIDIAN_API_URL", "OBSIDIAN_API_KEY"]:
        if key in os.environ:
            del os.environ[key]