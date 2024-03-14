import logging


class prefixMaker(logging.LoggerAdapter):
    def __init__(self, prefix, logger):
        super().__init__(logger)
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs
