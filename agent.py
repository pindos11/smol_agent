import os
import json
import urllib.request
import sys


from datetime import date

###custom imports (file unreadable as single file, so i did split)
import agent_definitions
import agent_tools
import agent_tools_runner
import agent_messages
import agent_printer
import agent_config

class modelRequest:
    def __init__(self,context,model):
        self.context = context
        self.model = model

    def composeSelf(self,want_reasoning):
        messages = self.context.composeSelf(want_reasoning)
        result = {
            "model": self.model,
            "messages": messages,
            "tools": agent_definitions.SYS_TOOLS,
            "tool_choice": "auto",
            "stream": True
        }
        return result

    def makeRequest(self, want_reasoning = True):
        result = urllib.request.Request(
            agent_definitions.url,
            data=json.dumps(self.composeSelf(want_reasoning)).encode(),
            headers={
                "Authorization": f"Bearer {agent_definitions.api_secret}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            method="POST"
        )

        return result

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



    def processStreamLine(self,data):
        line = data.decode("utf-8").strip()
        if line[:6] != "data: ":
            #what was called before???
            if(self.currently != "nothing"):
                self.prev = self.currently
            self.currently = "nothing"
            return

        ###debug result
        self.debug_result.append(line)
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


            if content != None:
                self.last_item = content
                if(self.prev == "reasoning"):
                    self.prev = "answer"
                    self.last_item = "\n\n"+content
                self.content+=content
                self.currently = "answer"

            if reasoning != None:
                self.reasoning+=reasoning
                self.currently = "reasoning"
                self.last_item = reasoning

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

        #lets try to get someting out of the call
        self.toolChunks.append(tool_call) 

    def finalize_tool(self):
        processor = agent_tools.agentToolsChunkParser()

        self.toolCalls = processor.processChunks(self.toolChunks)
    
    def isDone(self):
        return self.stopped

    def getMessage(self):
        return agent_messages.modelMessage("assistant",self.content,self.reasoning,self.toolCalls)


##################### execution here

### lets define model call function that will just take context and do all the job

def call_model(context, printer):
    # define object to process model's answer
    c_answer = modelAnswer()
    response = None

    try:
        #make http request
        m_request = modelRequest(context, agent_definitions.MODEL)
        req = m_request.makeRequest()

        #do actual call
        response = urllib.request.urlopen(req, timeout=60) #15 was too small. Need to handle it later
        for raw_line in response:
            c_answer.processStreamLine(raw_line)

            if c_answer.isDone():
                break

            #who knows, maybe its subject for animated printing?
            
            printer.printChunk(c_answer.last_item,c_answer.currently)
        
        #done with listening to answer. Lets return final model's message

        return c_answer
    except KeyboardInterrupt:
        printer.printEndMessage()
        printer.printSysMessage("Interrupted by user")
        return None

    finally:
        if response is not None:
            response.close()
    


config = agent_config.agentConfig()

session_context = agent_messages.modelTextContext()
systemMessage = agent_messages.modelMessage("system",agent_definitions.SYS_MESSAGE)
session_context.add_message(systemMessage)

screen_printer = agent_printer.cliPrinter(config)

toolRan = False

#now the loop for user

while(1):
    #let the user do input
    if toolRan == False:
        user_input = screen_printer.doInput("")
    else:
        user_input = ""

    match user_input:
        case "/context":
            toolRan = False
            to_save = json.dumps(session_context.composeSelf(True), indent=2)

            f = open("session.txt","w",encoding="utf-8")
            f.write(to_save)
            f.close()

        case "/exit":
            toolRan = False
            break

        case "/clear":
            toolRan = False
            session_context = agent_messages.modelTextContext()
            systemMessage = agent_messages.modelMessage("system",agent_definitions.SYS_MESSAGE)
            session_context.add_message(systemMessage)
            screen_printer.resetScreen()
            screen_printer.printSysMessage("Session reset")
        
        case _:
            toolRan = False
            if(user_input != ""):
                userMessage = agent_messages.modelMessage("user",user_input)
                session_context.add_message(userMessage)
            screen_printer.printEndMessage()

            answer = call_model(session_context,screen_printer)
            if answer is None:
                continue
            screen_printer.printEndMessage()
            

            #add all text gathered, and tool calls are added to message as well, so its not lost
            session_context.add_message(answer.getMessage())

            #now lets run tools
            for i in answer.toolCalls:
                toolRan = True
                runner = agent_tools_runner.agentToolRunner(i)
                check = runner.validateTool()
                errorText = f"Tool index {i.index} was not executed: "
                if check != 0:
                    #something is called wrong
                    match check:
                        case 1:
                            errorText += "Tool call failed, internal error"
                        case 2:
                            errorText += "Command is malformed"
                        case 3:
                            errorText += "Other than bash tool is used"
                        case _: #idk
                            errorText += "Tool call failed, internal error"
                    errorMessage = agent_messages.modelMessage("system",errorText)
                    session_context.add_message("system",errorMessage)
                    screen_printer.printMessage(errorMessage)
                    continue
                #as user if they wanna run it?
                user_answer = screen_printer.doInput(f"Command is: {runner.toolCall.command}. Want to run tool? Y/N: ", question=True)
                match user_answer:
                    case "Y": #lets try at least
                        toolCall = runner.executeTool() #needa think about it
                        ran_content = ""
                        if runner.result.returncode == 0:
                            ran_content = runner.result.stdout
                        else:
                            ran_content = runner.result.stderr
                        ranMessage = agent_messages.modelMessage("tool",ran_content,None,None,runner.composeSelf(),i.id)
                        session_context.add_message(ranMessage)
                        screen_printer.printMessage(ranMessage)
                    case _:
                        declinedMessage = agent_messages.modelMessage("system",errorText+"User declined execution")
                        session_context.add_message(declinedMessage)
                        screen_printer.printMessage(declinedMessage)
                
                


