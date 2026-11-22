
import agent_config
import agent_printer
import agent_api_request
import agent_messages
import agent_definitions
import agent_tools_runner
import agent_utils

class agentLoop:
    def __init__(self):
        #lets define current state just so its easy to use later

        #all possible states there can be in interaction with user
        self.possible_steps = [
            "user_prompt",
            "model_processing", #that is when user submitted their prompt
            "tool_calling" #that is when model tool call was accepted/declined by user. Next step will be "model_processing"
        ]

        self.allowed_commands = [ #maybe later can be turned to name methods in here as dict or something?
            "/context", #save context as file
            "/exit", #close script
            "/clear" #clear screen
        ]

        #its the step currently going on
        self.current_step = self.possible_steps[0]
        self.last_user_command = ""

        self.last_result = None

        self.run_ended = False

        #real logic classes now
        self.config = config = agent_config.agentConfig()
        self.printer = agent_printer.cliPrinter(config)
        self.session_context = agent_messages.modelTextContext()
        self.initSession() #while we are at it
        self.model_caller = agent_api_request.modelCaller()
        

    def initSession(self):
        #reset context
        self.session_context = agent_messages.modelTextContext()
        #put system peompt into there
        self.session_context.add_message(agent_messages.modelMessage("system",agent_definitions.SYS_MESSAGE))

    def dispatchCommand(self):
        #do technical comand. do what was asked and then return back to prompt
        utils = agent_utils.agentUtils()
        match self.last_user_command:
            case "/context":
                utils.save_session(self.session_context)
                self.printer.printSysMessage("Saved current session")
            case "/exit":
                #close for now idk
                exit()
            case "/clear":
                self.initSession()
                self.printer.resetScreen()
                self.printer.printSysMessage("Session reset")
        #done, go back to user input
        self.last_user_command = ""
        self.current_step = self.possible_steps[0]

    def nextStep(self):
        #thats where loop happens overall
        match self.current_step:
            case "user_prompt":
                self.userPrompt()
                if self.last_user_command != "":
                    self.current_step = self.possible_steps[1]
            case "model_processing": #if tool was called then tool_calling, otherwise - to user_prompt
                self.modelProcessing()
                if self.run_ended == True:
                    self.current_step = self.possible_steps[0]
                    self.run_ended = False
                else:
                    self.current_step = self.possible_steps[2]
            case "tool_calling": #from here we can only go to model_processing back
                self.toolCalling()
                self.current_step = self.possible_steps[1]
                

    def userPrompt(self):
        #here we have to ask user to enter the data
        self.last_user_command = self.printer.doInput("")

        #is it actual text or what? If not, we will ever exit this method only after user really gives prompt
        if self.last_user_command in self.allowed_commands:
            #its not prompt as it seems
            self.dispatchCommand()


    def modelProcessing(self):

        self.printer.printEndMessage()

        #well, the model gotten a message or a tool call result. Lets see, what we have
        if self.last_user_command != "":
            #we have a normal prompt submitted. Append it to message list
            userMessage = agent_messages.modelMessage("user",self.last_user_command)
            self.session_context.add_message(userMessage)
            self.last_user_command = ""

        #in here we just go and give context to model and let it work. Any toolcalls etc are already done
        self.last_result = self.model_caller.call_model(self.session_context,self.printer)

        if self.last_result == None:
            self.run_ended = True
            return

        #save what model did say to context
        self.session_context.add_message(self.last_result.getMessage())

        self.printer.printEndMessage()

        #maybe no tools even called? We can then avoid tool_calling step at all
        if len(self.last_result.toolCalls)==0:
            #we are done
            self.run_ended = True

    def toolCalling(self):
        #loop over tool calls, prompt user, run calls and then appens results per each call
        for i in self.last_result.toolCalls:
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
                self.session_context.add_message(errorMessage)
                self.printer.printMessage(errorMessage)
                continue
            #ask user if they wanna run it?
            user_answer = self.printer.doInput(f"\nCommand is: {runner.toolCall.command}. Want to run tool? Y/N: ", question=True)
            match user_answer:
                case "Y": #lets try at least
                    toolCall = runner.executeTool() #needa think about it
                    ran_content = ""
                    if runner.result.returncode == 0:
                        ran_content = runner.result.stdout
                    else:
                        ran_content = runner.result.stderr

                    self.printer.printEndMessage()

                    ranMessage = agent_messages.modelMessage("tool",ran_content,None,None,runner.composeSelf(),i.id)
                    self.session_context.add_message(ranMessage)
                    self.printer.printMessage(ranMessage)
                case _:
                    self.printer.printEndMessage()
                    declinedMessage = agent_messages.modelMessage("system",errorText+"User declined execution")
                    self.session_context.add_message(declinedMessage)
                    self.printer.printMessage(declinedMessage)

