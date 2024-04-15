import logging

from exastris_bot.botCore import ExBot
from json import load

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    path_to_config = "config.json"
    with open(path_to_config) as f:
        config = load(f)
    ExBot(config).run()
