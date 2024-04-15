from exastris_bot.handlers.MemberHandler import NewMemberHandler, MemberHandlerConfig, MemberJoinCallBack, \
    LeftMemberHandler
from telegram.ext import JobQueue

Handlers = [
    NewMemberHandler,
    LeftMemberHandler,
    MemberJoinCallBack
    ]
init_handlers = [
    MemberHandlerConfig.init_config

]
job_queue = JobQueue()
