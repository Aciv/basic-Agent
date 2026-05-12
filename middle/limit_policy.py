from memory.memory import Context, Message
from typing import Callable, List

class truncate_policy:
    def __init__(self, truncated_type = 'Message', truncated_limit = 100):
        self.truncated_type = truncated_type
        self.truncated_limit = truncated_limit

    def __call__(self, context : Context):
        if context.get_current_len() < self.truncated_limit:
            return
        
        print("let truncted")
        context.read_pos = context.count
        context.append(context.system_prompt)


class summarize_policy:
    def __init__(self, summarize_agent: Callable[[List[Message]], Message],
                summarized_type = 'Message',summarized_limit = 100):
        self.truncated_type = summarized_type
        self.truncated_limit = summarized_limit
        self.summarize_agent = summarize_agent


    def __call__(self, context : Context):
        if context.get_current_len() < self.truncated_limit:
            return
        
        summarized_message = self.summarize_agent(context)

        context.read_pos = context.count
        context.append(context.system_prompt)
        context.append(summarized_message)