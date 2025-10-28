import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so top-level modules (e.g., utils) resolve
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Disable LangSmith tracing if misconfigured
# os.environ.pop("LANGCHAIN_TRACING_V2", None)
# os.environ.pop("LANGCHAIN_ENDPOINT", None)

from arithmetic_agent import graph as arithmetic_graph
from greeting_workflow import graph as greeting_graph
from post_meeting_workflow import graph as post_meeting_graph
from langchain_core.messages import HumanMessage


def main() -> None:
    # prompt = "what is 43+2?" if len(sys.argv) == 1 else " ".join(sys.argv[1:])
    # result = arithmetic_graph.invoke({"messages": [HumanMessage(content=prompt)]})
    # print(result)

    prompt = """
Date: October 22, 2025
Duration: 27 minutes
Participants:
Alex (AE) - Snowflake Account Executive
Jamie (CT) - Director of Data Engineering at FreshMart (a national grocery retailer)

Call:
Alex (AE): Hey Jamie, thanks for hopping on today. How have things been going with your data platform initiative?

Jamie (CT): Pretty good! We've fully migrated our transactional data into Snowflake now, and we're working on consolidating our real-time inventory feeds.

Alex (AE): That's awesome. I also wanted to share a couple of new features that recently launched — one is Snowpark Container Services, which lets you run containerized workloads directly inside Snowflake. The other is Cortex, our AI/ML suite that brings foundation models and embeddings natively into the platform.

Jamie (CT): Interesting. We've actually been exploring some AI use cases, like demand forecasting for perishable goods and product recommendations in our mobile app. Right now, we're experimenting with that outside of Snowflake.

Alex (AE): Got it — so you're exporting data to a separate environment for modeling?

Jamie (CT): Exactly. We use Databricks for that, and it's been a bit of a headache keeping the two in sync.

Alex (AE): Yeah, that's a common challenge. With Cortex, you could run those same models — or even fine-tune foundation models — inside Snowflake without data movement. That might simplify things.

Jamie (CT): That would definitely be appealing. We've also been looking at a real-time pricing optimization use case, but latency's been an issue.

Alex (AE): Snowpark Container Services could help there — you can deploy microservices that respond to streaming events directly in Snowflake.

Jamie (CT): Oh, that's cool. We've been thinking about using Kafka for that, but I didn't realize Snowflake could host the service logic itself.

Alex (AE): Yep — and you can integrate it with Snowpipe Streaming or your Event Tables for a closed loop.

Jamie (CT): Nice. Maybe we could pilot that with the pricing model.

Alex (AE): Absolutely. Would you be open to a short technical workshop with our solution architect to map out what that could look like?

Jamie (CT): Sure, that'd be helpful. Maybe early November?

Alex (AE): Perfect. I'll send over a few time slots. Before we wrap, any blockers or concerns you're seeing with your current workloads in Snowflake?

Jamie (CT): Only thing — we've noticed costs going up a bit with the new query volumes. Finance is asking for more visibility into cost attribution by team.

Alex (AE): Good callout. We can look into Cost Governance Dashboards and object tagging to give you better visibility. I'll include that in the follow-up.

Jamie (CT): Great, thanks.

Alex (AE): Awesome — I'll send a summary with next steps, workshop invite, and some Cortex docs. Appreciate your time today!

Jamie (CT): Likewise. Looking forward to the follow-up.
    
    """
    result = post_meeting_graph.invoke({"call_transcript": prompt})
    print(result)


if __name__ == "__main__":
    main()
