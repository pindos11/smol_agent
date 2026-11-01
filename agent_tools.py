import json

class agentToolCall:
    def __init__(self, index, id, name = None, args = None):
        self.index = index
        self.id = id
        self.name = name

        self.command = ""
        self.setArgs(args)

        self.partName = ""
        self.partArgs = ""

    def setArgs(self,args):
        self.args = args
        if self.args != None:
            argu = json.loads(self.args)
            self.command = argu.get("command")

    def finalize(self): #use that when all chunks are done
        self.name = self.partName
        self.setArgs(self.partArgs)

    def composeSelf(self): #thats a part of context as well. We retain tool call data and give it back to model
        result = { #i think no index yeah?
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.args #that actually is dict type as string, but tool call is a bit different
            }
        }

        return result

class agentToolsChunkParser:
    def __init__(self):
        #maybe there has to be something, but idk really. For now ok
        return

    def processChunks(self,chunks):
        #we have several important items per chunk
        self.toolCalls = []

        for i in chunks:
            #it is a list, so there MAY be several things
            for j in i:
                index = j.get("index")
                if index == None:
                    continue
                curTool = None
                if len(self.toolCalls)<index+1: #new tool call
                    #if its new tool, there shoulda be id
                    id = j.get("id")
                    if id == None:
                        continue #bruh
                    curTool = agentToolCall(index,id)
                    self.toolCalls.append(curTool)
                else:
                    curTool = self.toolCalls[int(index)]

                #cool stuff, now lets fill current tool call with chunk's data
                func = j.get("function",{})
                name = func.get("name")
                if name != None:
                    curTool.partName += name

                argument = func.get("arguments")
                if argument != None:
                    curTool.partArgs += argument
                self.toolCalls[int(index)] = curTool

        #cool, done with chunks

        for i in self.toolCalls:
            i.finalize()

        return self.toolCalls
