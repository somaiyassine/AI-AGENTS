# AGENT 1 : MEMORY & BASIC TOOLS
# lahne na3mlou awel agent sghir: assistant personnel 3andou tool wa7da (ta3tik l wa9t)
# w 3andou memory bech yetfakar chnowa 9otlou fel messaget eli fetou.

import logging
from datetime import datetime

from dotenv import load_dotenv
from agentspan.agents import Agent, AgentRuntime, ConversationMemory, run, tool

# na9raw les variables mta3 l .env (kima AGENTSPAN_SERVER_URL) bech yod5lou lel environment
load_dotenv()

# nsaktou les logs zeydin mta3 agentspan w conductor, nkhaliw ken les warnings
logging.basicConfig(level=logging.WARNING)
logging.getLogger("agentspan").setLevel(logging.WARNING)
logging.getLogger("conductor").setLevel(logging.WARNING)

# @tool t7awel l function hedhi l tool ynajem l LLM y3ayatelha wa9t yest7a9ha
# l docstring mohem barcha: houwa eli y9ra fih l model bech yefhem l tool chnowa ta3mel
@tool
def get_current_time() -> str:
    """returns the current local time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# l memory mta3 l conversation: tkhabi e5er 50 message bech l agent yetfakar l kleem eli fet
conversation_memory = ConversationMemory(max_messages=50)

# lahne n3arfou l agent:
# - name: esmou
# - model: l model eli ykhdem bih (Gemini 2.5 Flash)
# - instructions: l system prompt, kifech lezmou yetsarref
# - tools: les tools eli ynajem yesta3melhom
# - memory: l memory eli yetfakar biha
assistant = Agent(name="personal_assistant",
                  model="google_gemini/gemini-2.5-flash",
                  instructions=(
                    "You are a concise personal assistant. Use tools when they help"
                    "and remember useful user details across turns"
                  ),
                  tools=[get_current_time],
                  memory=conversation_memory,
)
if __name__ == "__main__":
    print("Starting agent...")
    # l AgentRuntime yetconnecta bel server mta3 agentspan (lezmou ykoun cha3el 9bal)
    # w l "with" tdhmenelna eli yetsaker mli7 wa9t nkamlou
    with AgentRuntime() as runtime:
        # boucle chat: na9raw mel user lin yekteb "q"
        while True:
            prompt = input("You: ").strip()
            if prompt.lower() == "q" :
                break
            # ken l user ma kteb chay, n3awdou nas2louh
            if not prompt:
                continue
            # nab3thou l prompt lel agent w nestanew l jaweb
            result = run(assistant, prompt, runtime=runtime)
            # l jaweb yji dict, l texte l 7a9i9i mawjoud fel cle "result"
            readable_result = result.output.get('result')
            # nzidou l so2el w l jaweb lel memory b yedina bech yetfakarhom fel dawra jeya
            conversation_memory.add_user_message(prompt)
            conversation_memory.add_assistant_message(readable_result)
            print(f"Assistant: {readable_result}")
