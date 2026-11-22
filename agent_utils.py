import json

class agentUtils():
    def save_session(self,context):
        to_save = json.dumps(context.composeSelf(True), indent=2)
        
        f = open("session.txt","w",encoding="utf-8")
        f.write(to_save)
        f.close()