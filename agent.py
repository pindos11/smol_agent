###custom imports (whole implementation is unreadable as single file, so i did split)
import agent_loop


##################### execution here

loop_runner = agent_loop.agentLoop()

#now the loop for user

while(1):
    loop_runner.nextStep()
                
                


