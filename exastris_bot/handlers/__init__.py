from exastris_bot.handlers.MemberHandler import MemberHandler,MemberHandlerConfig,MemberJoinCallBack
from telegram.ext import JobQueue

Handlers = [
    MemberHandler,
    MemberJoinCallBack
    ]
init_handlers = [
    MemberHandlerConfig.init_config

]
job_queue = JobQueue()
