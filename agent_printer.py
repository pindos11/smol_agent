import sys
import os

import random

class cliPrinter:
    def __init__(self,agent_config = None):
        self.use_color = (
            sys.stdout.isatty()
            and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") != "dumb"
        )


        colors = {}
        zen_params = {}
        if agent_config != None:
            colors = agent_config.get_text_colors()
            zen_params = agent_config.get_zen_params()

        self.thinkColor = colors.get("think_escape","")
        self.answerColor = colors.get("answer_escape","")
        self.userColor = colors.get("user_escape","")
        self.systemColor = colors.get("system_escape","")
        self.toolColor = colors.get("tool_escape","")
        self.questionColor = colors.get("question_escape","")

        self.resetColor = "\033[0m" #reset to as it was

        #animated text enjoyment
        self.animText = ""
        self.type = ""
        self.animStyle = self.systemColor
        self.animStep = 0

        #zen settings
        self.zen_mode = zen_params.get("zen_mode", False)
        self.zen_think_texts = zen_params.get("zen_think_texts",["Thinking"])
        self.zen_tool_call_texts = zen_params.get("zen_tool_call_texts",["Tool calling"])

        #texts for dilly-dallying
        self.thinkText = ""
        self.toolText = ""


    
    def printChunk(self,content,type):
        color = ""
        result = content
        match type:
            case "reasoning":
                color = self.thinkColor
            case "answer":
                color = self.answerColor
            case "tool":
                color = self.toolColor
                #do we want to limit max chars?
            case _:
                return

        self.printColorized(color,result)

    def printMessage(self,message):
        color = ""
        match message.role:
            case "tool":
                color = self.toolColor
            case "system":
                color = self.systemColor
        print("\n")
        content = message.content.strip("\r\n")
        self.printColorized(color,"\n"+content)
        return

    def printColorized(self,color,content):
        if self.use_color == True:
            print(f"{color}{str(content)}{self.resetColor}", end = "", flush = True)
        else:
            print(f"{content}", end = "", flush = True)
        return

    def doInput(self,prompt, question=False):
        user_prompt = ""
        if self.use_color == False:
            user_prompt = prompt
        else:
            if question == False:
                user_prompt = f"{self.userColor}{prompt}"
            else:
                user_prompt = f"{self.questionColor}{prompt.center(len(prompt)+5)}{self.resetColor}{self.userColor}"

        try:
            return input(user_prompt)
        finally:
            if self.use_color == True:
                sys.stdout.write(self.resetColor)
            sys.stdout.flush()

    def printEndMessage(self,text = ""):
        if(text==""):
            print("\n\n")
        else:
            print("\n")
            self.printSysMessage(text)

    def printSysMessage(self, message):
        cur_message = message
        if self.use_color == True:
            cur_message = f"{self.systemColor}{str(message).center(len(message)+5)}{self.resetColor}"
        print(cur_message)
        print("\n")

    def resetScreen(self):
        if sys.stdout.isatty():
            print("\033[2J\033[H", flush=True) #seems to be easier
        #if sys.platform == "win32":
        #    os.system("cls")
        #else:
        #    os.system("clear")
    
    def pick_random_texts(self):
        self.thinkText = random.choice(self.zen_think_texts)
        self.toolText = random.choice(self.zen_tool_call_texts)

    def printAnimatedText(self,type,text=""): #that ends up being a proxy to zen mode
        #for now that, but idk. Would need to \r line maybe. Maybe redundant
        result = ""
        do_Dots = False
        #i need to build like next item with animation
        match type:
            case "tool":
                if self.zen_mode == True:
                    if self.type != type:
                        self.type = type
                        result = "\n"
                    result += f"\r\033[2K{self.toolText}"
                    do_Dots = True
                else:
                    result = text
            case "reasoning":
                if self.zen_mode == True:
                    if self.type != type:
                        self.type = type
                        result = "\n"
                    result += f"\r\033[2K{self.thinkText}"
                    do_Dots = True
                else:
                    result = text
            case _:
                result = text

        if do_Dots == True:
            result += "."*self.animStep
            self.animStep += 1

            if self.animStep > 4:
                self.animStep = 0

        #lets now print chunk
        self.printChunk(result,type)