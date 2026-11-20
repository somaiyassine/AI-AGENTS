
# AGENT 2 : RAG, GUARDRAILS AND HITL (Human In The Loop)
# lahne na3mlou agent mta3 customer support:
# - RAG: ylawej fel knowledge base (docs) 9bal ma yjaweb
# - Guardrails: yblocki les prompts eli fihom 7aja mech normal (prompt injection)
# - HITL: 9bal ma ya3mel refund, ya9ef w yestana insen yvalidi (y/n)

import logging

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agentspan.agents import (
    Agent,
    AgentRuntime,
    ConversationMemory,
    EventType,
    Guardrail,
    GuardrailResult,
    OnFail,
    Position,
    guardrail,
    start,
    tool,
)


# override=True: les variables mta3 l .env yeghelbou 3al eli mawjoudin fel environment
load_dotenv(override=True)
# nsaktou les logs mta3 INFO lkol, nkhaliw ken WARNING w fou9
logging.basicConfig(level=logging.WARNING, force=True)
logging.disable(logging.INFO)


# base de donnees fake (mock) blaset DB 7a9i9ia, fiha commande wa7da w compte wa7ed
MOCK_DB = {
    "orders": {"A100": {"status": "delivered", "total": 49.99}},
    "accounts": {"tim@example.com": {"status": "active", "tier": "pro"}},
}

# les docs mta3 l support: hedhi hiya l "knowledge base" eli ye5dem 3liha l RAG
DOCS = {
    "refund policy": "Refunds are processed within 5 business days.",
    "shipping": "Standard shipping takes 3 to 7 business days.",
    "account": "Pro accounts include priority support.",
}


# structured output: nfardhou 3al agent yraja3 jaweb b chakl hedha (pydantic model)
# 3oudh ma yraja3 texte 3adi, yraja3 stage + successful + message
class SupportResponse(BaseModel):
    stage: str = Field(description="Stage like answered, refunded or rejected")
    successful: bool
    message: str


# tool mta3 l RAG: tlawej 3la titre doc mawjoud fel so2el w traja3 l contenu mte3ou
# (recherche sghira bel klem, mech embeddings, ama l fekra hiya hiya)
@tool
def search_knowledge_base(query: str) -> str:
    """search support docs"""
    for title, body in DOCS.items():
        if title in query.lower():
            return body
    return "No mtahcing support articles found."


# tool tjib les infos mta3 commande mel DB bel ID mte3ha
@tool
def lookup_order(order_id: str) -> dict:
    """lookup order in database by ID"""
    return MOCK_DB["orders"].get(order_id, {"error": "order not found"})


# approval_required=True: lahne l HITL
# wa9t l agent y7eb y3ayet lel tool hedhi, l workflow ya9ef (WAITING)
# w yestana insen ya3mel approve wala reject 9bal ma tetnaffedh
@tool(approval_required=True)
def process_refund(order_id: str, amount: float) -> str:
    """request a refund, pause for human approvla think before you run this"""
    return f"Refunded {amount:.2f} for order {order_id}"


# guardrail 3al input: ythabet fel prompt 9bal ma yousel lel model
# ken l9a kelma mech normal (ignore, jailbreak...) yraja3 passed=False
@guardrail
def safe_support_request(prompt: str) -> GuardrailResult:
    """Block obvious prompt injection attempts"""
    blocked = ["ignore", "ignore previous", "system prompt", "jailbreak"]
    passed = not any(phrase in prompt.lower() for phrase in blocked)
    return GuardrailResult(passed=passed, message="Please ask a normal question, this is blocked.")


# l agent mta3 l support, njam3ou fih kol chay:
# - instructions: nfasroulou les etapes (knowledge base lowel, lookup_order, ba3d process_refund)
# - output_type: l jaweb lezmou ykoun SupportResponse
# - tools: les 3 tools eli fou9
# - memory: yetfakar e5er 50 message
# - guardrails: n7ottou l guardrail 3al INPUT, w ken faila ya3mel RAISE (exception)
# - max_turns: maximum 10 dawrat bech ma yod5olch fi boucle ma toufech
support_agent = Agent(
    name="support_agent",
    model="google_gemini/gemini-2.5-flash",
    instructions=(

        "You are a customer support agent. Use the knowledge base first. "
        "If the customer wants a refund: when you know the order ID, call "
        "lookup_order to get the amount. Before calling process_refund, "
        "write a short plain-English sentence describing exactly what refund "
        "you are about to issue, for example: 'I am going to refund $49.99 "
        "for order A100.' Then call process_refund. The tool will pause for "
        "human approval automatically. If the order ID is missing, ask the "
        "customer for it. Always populate the message field with a clear reply."
    ),
    output_type=SupportResponse,
    tools=[search_knowledge_base, lookup_order, process_refund],
    memory=ConversationMemory(max_messages=50),
    guardrails=[Guardrail(safe_support_request, position=Position.INPUT, on_fail=OnFail.RAISE)],
    max_turns=10
)

# nkhadmou l agent b stream bech nchoufou les events wa7da b wa7da (tool call, result, waiting...)
def run_interactive(prompt: str) -> None:
    with AgentRuntime() as runtime:
        # start (mech run): ybda l execution w yraja3lna handle netcontroliw bih (approve/reject)
        handle = start(support_agent, prompt, runtime=runtime)
        stream = handle.stream()

        # nkhabiw l order_id w l amount bech nwarriwhom lel user wa9t notolbou l validation
        order_id, amount = None, None
        for event in stream:
            # ki l agent y3ayet l tool, nekhdhou l order_id mel args mte3ha
            if event.type == EventType.TOOL_CALL and event.args:
                order_id = event.args.get("order_id") or order_id
            # ki yarja3 resultat mta3 lookup_order (dict), nekhdhou menou l total
            elif event.type == EventType.TOOL_RESULT and isinstance(event.result, dict):
                amount = event.result.get("total") or amount
            # WAITING = l workflow wa9ef yestana validation mta3 insen (process_refund)
            elif event.type == EventType.WAITING:
                print(f"\nApproval required: refund ${amount:.2f} for order {order_id}")
                decision = input("Approve? (y/n): ").lower().strip()
                if decision == "y":
                    handle.approve()
                else:
                    handle.reject("user rejected")

        # ba3d ma youfa l stream, nekhdhou l resultat final w ntab3ouh
        result = stream.get_result()
        output = result.output.get("result")
        print(f"\n{output}\n")


if __name__ == "__main__":
    print("Support bot starting....")
    # boucle chat 3adia: "q" bech to5rej
    while True:
        prompt = input("You: ").strip()
        if prompt.lower() == "q":
            break
        if not prompt:
            continue
        run_interactive(prompt)
