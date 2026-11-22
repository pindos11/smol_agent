import json

import agent_tools
import agent_messages

class modelAnswer():
    def __init__(self):
        self.content = ""
        self.reasoning = ""
        self.stopped = False
        self.debug_result = []
        self.last_item = ""
        self.currently = "reasoning"
        self.prev = "reasoning"
        self.toolCalls = []

        self.last_reasoning = ""
        self.last_content = ""
        self.last_tool = ""



    def processStreamLine(self,data):

        #maybe its blank chunk
        self.last_reasoning = ""
        self.last_content = ""
        self.last_tool = ""

        line = data.decode("utf-8").strip()
        if line[:6] != "data: ":
            #what was called before???
            if(self.currently != "nothing"):
                self.prev = self.currently
            self.currently = "nothing"
            return

        ###debug result
        self.debug_result.append(line)
        #print(line) ##maybe if you want to see what comes from server
        ###debug end
        
        update = line[6:]
        if update == '[DONE]':
            self.stopped = True
            return

        #print(update)

        update_j = json.loads(update)

        for item in update_j.get("choices",[]):
            delta = item.get("delta",{})
            reasoning = delta.get("reasoning_content")
            content = delta.get("content")
            tool_calls = delta.get("tool_calls")
            finish_reason = item.get("finish_reason")


            #we build a set of last items for everything supported. We literally print
            #everything that comes, no mater it is tool calling now or whatever.
            #faithful strategy + interactiveness, but it may look bad in case
            #some api gives reasoning after content, or something combined with tool call



            if reasoning != None:
                self.reasoning+=reasoning
                self.currently = "reasoning"
                self.last_item = reasoning
                self.last_reasoning = reasoning
            
            if content != None:
                self.last_item = content
                if(self.prev == "reasoning"):
                    self.prev = "answer"
                    self.last_item = "\n\n"+content
                self.last_content = self.last_item #fixing
                self.content+=content
                self.currently = "answer"

            if tool_calls != None:
                self.process_tool(tool_calls)

            if finish_reason == "tool_calls":
                self.process_tool(None,True)
                self.stopped = True
                self.calledTool = True

    def process_tool(self,tool_call = None, end = False):
        #tool call ended, so we need to go further
        if end == True:
            self.finalize_tool()
            return


        #tell the user its now a tool call
        if(self.prev != "tool"):
            self.last_item = "\n\ntool calling"
            self.currently = "tool"
            self.toolChunks = []
            self.prev = "tool"
        else:
            self.currently = "tool"
            self.last_item = "."
            if len(self.toolChunks)%4 == 0:
                self.last_item = "\r\033[2Ktool calling"

        self.last_tool = self.last_item

        #lets try to get someting out of the call
        self.toolChunks.append(tool_call) 

    def finalize_tool(self):
        processor = agent_tools.agentToolsChunkParser()

        self.toolCalls = processor.processChunks(self.toolChunks)
    
    def isDone(self):
        return self.stopped

    def getMessage(self):
        return agent_messages.modelMessage("assistant",self.content,self.reasoning,self.toolCalls)