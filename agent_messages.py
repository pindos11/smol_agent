import json

class modelMessage:
    def __init__(self,role,content = None,reasoning = None, toolCalls = None, toolResults = None, tRID = None):
        self.role = role
        self.content = content
        self.reasoning = reasoning
        self.toolCalls = toolCalls #that will be a list all the time. Thats for role "assistant"
        self.toolResults = toolResults #i assume its a list too. Thats for role "tool"
        self.toolCallId = tRID #tool call result id
    
    def composeSelf(self,want_reasoning = True):
        result = {}
        if self.content == None and self.reasoning == None and self.toolCalls == None and self.toolResults == None:
            return

        result.update({
            "role": self.role
        })

        if self.content != None:
            result.update(
                {
                    "content": self.content
                }
            )

        if self.reasoning != None or self.reasoning == '' and want_reasoning == True:
            result.update(
                {
                    "reasoning_content": self.reasoning
                }
            )

        if self.toolCalls != None:
            toolCallsData = []
            for i in self.toolCalls:
                toolCallsData.append(i.composeSelf())
            result.update(
                {
                    "tool_calls": toolCallsData
                }
            )

        if self.toolResults != None:
            result.update(
                {
                    "tool_call_id": self.toolCallId,
                    "content": json.dumps(self.toolResults)
                }
            )
 
        return result

class modelTextContext:
    def __init__(self):
        self.messages = []
        return

    def add_message(self,message):
        self.messages.append(message)

    def composeSelf(self,want_reasoning = True):
        messages = []
        for i in self.messages:
            messages.append(i.composeSelf(want_reasoning))
        return messages