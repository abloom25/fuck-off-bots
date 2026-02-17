#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# Initialize NoneBot
nonebot.init()

# Register Adapter
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# Load Builtin Plugins
nonebot.load_builtin_plugins("echo")

# Load Other Plugins
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
