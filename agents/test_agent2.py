# TEST mta3 AGENT 2
# mock_run ykhadem l agent bla LLM 7a9i9i w bla server:
# a7na na3tiwh les events (tool call, tool result, done) eli n7ebouhom "ysirou"
# w ba3d nthabtou eli l agent tsarref kima nestanew
from agentspan.agents.testing import MockEvent, expect, mock_run

from agent2 import SupportResponse, support_agent


# l resultat fake eli bech traj3ou l tool mta3 l knowledge base
REFUND_POLICY = "Source: support-policy.txt\nRefunds are processed within 5 business days."


def test_support_bot_refund_policy() -> None:
    # nsimuliw scenario: l user yas2el 3al refund policy
    result = mock_run(
        support_agent,
        "What is the refund policy?",
        events=[
            # 1. l agent y3ayet l search_knowledge_base
            MockEvent.tool_call("search_knowledge_base", {"query": "refund policy"}),
            # 2. l tool traja3 l policy
            MockEvent.tool_result("search_knowledge_base", REFUND_POLICY),
            # 3. l agent ykamel w yraja3 jaweb final b chakl SupportResponse
            MockEvent.done(
                SupportResponse(
                    stage="answered",
                    successful=True,
                    approval_required=False,
                    message="Based on our policy, refunds are processed within 5 business days.",
                )
            ),
        ],
    )

    # nthabtou: l run kmel, l jaweb fih kelmet "refund", ista3mel l tool s7i7a bel args s7a7, w ma famech errors
    expect(result).completed().output_contains("refund").used_tool(
        "search_knowledge_base", args={"query": "refund policy"}
    ).no_errors()


# tnajem tkhadmou b pytest wala direct b python
if __name__ == "__main__":
    test_support_bot_refund_policy()
    print("Mock test passed.")
