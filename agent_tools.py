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
        # keyed by index so gaps (e.g. a skipped chunk with no id) don't break
        # assignment-by-index, which used to raise IndexError on non-sequential calls.
        tools_by_index = {}

        for i in chunks:
            #it is a list, so there MAY be several things
            for j in i:
                index = j.get("index")
                if index == None:
                    continue
                index = int(index)
                if index not in tools_by_index:
                    #if its new tool, there shoulda be id
                    id = j.get("id")
                    if id == None:
                        continue #can't create a tool without an id
                    tools_by_index[index] = agentToolCall(index,id)

                curTool = tools_by_index[index]

                #cool stuff, now lets fill current tool call with chunk's data
                func = j.get("function",{})
                name = func.get("name")
                if name != None:
                    curTool.partName += name

                argument = func.get("arguments")
                if argument != None:
                    curTool.partArgs += argument

        #emit in index order so tool index in context/reporting stays stable
        self.toolCalls = [tools_by_index[k] for k in sorted(tools_by_index)]

        #cool, done with chunks

        for i in self.toolCalls:
            i.finalize()

        return self.toolCalls
