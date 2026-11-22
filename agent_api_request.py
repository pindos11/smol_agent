import urllib.request
import json

import agent_definitions
import agent_answer

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

class modelCaller:
    def call_model(self,context,printer):
        # define object to process model's answer
        c_answer = agent_answer.modelAnswer()
        response = None

        try:
            #ui kek
            printer.pick_random_texts()
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
                #we may want to replace reasoning tokens with "Thinking" animation

                #we have to understand that in fact, model api can emit many things. Lets print all one by one
                #if c_answer.currently != "nothing":
                #    print("\n\n---Chunk---")

                #reasoning
                if(c_answer.last_reasoning != ""):
                    printer.printAnimatedText("reasoning",c_answer.last_reasoning)

                #now content
                if(c_answer.last_content != ""):
                    printer.printAnimatedText("answer",c_answer.last_content)

                #now maybe tool call too
                if(c_answer.last_tool != ""):
                    printer.printAnimatedText("tool",c_answer.last_tool)

                #printer.printAnimatedText(c_answer.currently,c_answer.last_item)
                
            
            #done with listening to answer. Lets return final model's message
            return c_answer
        except KeyboardInterrupt:
            printer.printEndMessage()
            printer.printSysMessage("Interrupted by user")
            return None

        finally:
            if response is not None:
                response.close()