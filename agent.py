
###custom imports (whole implementation is unreadable as single file, so i did split)
import agent_definitions
import agent_tools_runner
import agent_messages
import agent_printer
import agent_config
import agent_api_request
import agent_loop


##################### execution here

loop_runner = agent_loop.agentLoop()

#now the loop for user

while(1):
    loop_runner.nextStep()
                
                


