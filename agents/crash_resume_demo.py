# CRASH & RESUME DEMO (durable execution)
# l fekra: agentspan ykhabi l state mta3 l workflow fel server
# ya3ni ken l script ta7 (Ctrl+C wala crash) fi wosst l khedma, najmou nkamlou mel blasa eli w9efna fiha
# kifech tjarabha:
#   1. 7ot MODE = "start" w khadem l script, copie l Execution ID eli ytab3ou
#   2. o9tel l script fel wosst (Ctrl+C) ba3d chwaya steps
#   3. 7ot MODE = "resume" w 7ot l ID fi EXECUTION_ID w 3awed khadmou => ykamel mel step eli w9ef fiha
import time

from dotenv import load_dotenv

from agentspan.agents import Agent, AgentHandle, AgentRuntime, EventType, start, tool


load_dotenv(override=True)

MODE = "resume"  # "start" bech tebda execution jdida, "resume" bech tkamel wa7da 9dima
EXECUTION_ID = "43eb6616-1db8-4e86-a452-171746c7ca9b"  # 7ot lahne l ID eli ytba3 fel mode start


# tool bati2a b 9assd (3 secondes) bech ykoun 3andek l wa9t to9tel l script fel wosst
# timeout_seconds=30: ken l tool tawlet akthar men 30 seconde, tet3tbar failed
@tool(timeout_seconds=30)
def slow_step(step: int) -> str:
    """Run one slow workflow step."""
    time.sleep(3)
    return f"Finished step {step}"


# agent y3ayet l slow_step 3achra marrat bel tartib
# max_turns=20: lezmou ykoun akbar men 10 bech yel7a9 ykamel les steps lkol
durable_agent = Agent(
    name="durable_demo_agent",
    model="google_gemini/gemini-2.5-flash",
    instructions=(
        "Run a 10-step workflow by calling slow_step once for each step, "
        "from 1 through 10, in order. Do not skip steps."
    ),
    tools=[slow_step],
    max_turns=20,
)


# ntab3ou les events mta3 l execution wa7da b wa7da lin tousel DONE
def stream_handle(handle: AgentHandle) -> None:
    print("Execution ID:", handle.execution_id)
    for event in handle.stream():
        print(event.type, getattr(event, "message", ""))
        if event.type == EventType.DONE:
            break


if __name__ == "__main__":
    with AgentRuntime() as runtime:
        if MODE == "start":
            # nebdew execution jdida
            handle = start(durable_agent, "Run the 10-step workflow.", runtime=runtime)
            stream_handle(handle)
        elif MODE == "resume":
            # nsajlou l agent ka worker (blocking=False bech l code ykamel) bech les tools yarj3ou ykhdmou
            runtime.serve(durable_agent, blocking=False)
            # netconnectiw bel execution l 9dima bel ID mte3ha w nkamlou ntab3ouha
            handle = AgentHandle(execution_id=EXECUTION_ID, runtime=runtime)
            stream_handle(handle)
        else:
            raise ValueError(f"Unknown MODE: {MODE}")
