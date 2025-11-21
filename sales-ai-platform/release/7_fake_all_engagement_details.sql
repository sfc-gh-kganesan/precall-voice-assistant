-- Create a fake all_engagement_details table for testing
create or replace table ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic (
CRM_ACCOUNT_NAME VARCHAR,
TYPE VARCHAR(11),
ACTIVITY_ID VARCHAR,
SALESFORCE_ACCOUNT_ID VARCHAR,
PARTICIPANT_NAMES VARCHAR,
SUBJECT VARCHAR,
RAW_CONTENT VARCHAR,
OWNER_ID VARCHAR,
TAKEAWAYS VARCHAR,
ACTIVITY_DATE DATE,
USER_COLUMN ARRAY,
DS DATE
);
insert into ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic select
'CompanyA', 
'MEETING', 
'9chdhagbdhajj5jlj95584unajgljfdg94u8585', 
'00184759847rG98TAU78', 
'Sarim from Snowflake, Kirk from Snowflake, Howard from Snowflake, Seth from Snowflake, John from CompanyA', 
'Future Sys Status Meeting',
$$
1212111: Hello. How's it going?
3444433: Good. You?
5556655: Got back from vacation in Denver. It was a blast.
788778888: Welcome back.
5556655: Thank you.; You're not a lakers fan.; Are you?
1212111: No. Warriors.
5556655: Good for you. Lakers really struggled last night.;
1212111: Warriors haven't been great this year either.
5556655: That's true.
1212111: Let's get started. I just wanted to check in to see how everything is going.
788778888: Things are good. Busy quarter. We've got a couple of big data initiatives running in parallel right now.
3444433: Always a good problem to have. Are those analytics-focused or more on the operational side?
788778888: Bit of both, actually. We're modernizing some internal dashboards and also trying to consolidate some of our supply chain data. Right now, that's sitting in a mix of SQL Server and S3 buckets.
5556655: Got it. So you're still hybrid—some on-prem, some cloud?
788778888: Yeah, unfortunately. We've made progress, but we're not fully cloud-native yet.
1212111: That's pretty common. Most of our customers are in that transition phase. What's the main driver behind the move? Cost? Speed? Analytics flexibility?
788778888: Mostly flexibility. Our analytics team keeps complaining that it takes too long to get new data sources connected. Every time they want to add something new, it becomes a small project.
3444433: Yeah, the integration tax. Snowflake can help simplify that quite a bit, especially if you start consolidating those sources in one place. Have you had a chance to look at Snowflake's data sharing features?
788778888: We've heard about them, but I don't think we're using them directly.
5556655: Data sharing's been one of the biggest unlocks for a lot of customers we work with. It lets you share live data across departments or even with partners without moving or copying files. So, for example, if you wanted your analytics team to pull supply chain data directly, they could query it instantly—no pipelines or duplication.
788778888: That would actually solve a big pain for us. We've got weekly batch jobs that try to keep marketing and operations data in sync, and they fail half the time.
1212111: What's your current tool stack for that?
788778888: We use Fivetran for some pipelines, and then some homegrown scripts. We also have a little bit of Databricks for transformation. It's a bit messy.
3444433: Totally understandable. It's a common story. When teams move fast, the architecture tends to sprawl.
5556655: If you're using Fivetran, you could actually connect that directly to Snowflake and eliminate a lot of those custom scripts.
788778888: Yeah, our data engineer mentioned that. I think the hesitation has been cost. People keep saying Snowflake gets expensive if you don't manage compute tightly.
1212111: That's a fair concern. And you're right—Snowflake gives you a lot of flexibility, but with that comes the need for some governance. Have you looked into auto-suspend and auto-resume on virtual warehouses?
788778888: No, not really.
5556655: It's basically a feature that automatically shuts down compute when it's idle and restarts it when someone queries. It keeps costs down without requiring someone to manually stop things.
788778888: Oh, that's nice. We could definitely use that. Our dev team leaves clusters running overnight constantly.
3444433: Yeah, that's like leaving the lights on. Easy to fix once you've got the right controls in place.
1212111: By the way, are you still mainly using Tableau for visualization?
788778888: Yep. Tableau for most things, and then Power BI for a couple of executive dashboards.
5556655: Got it. Snowflake works great with both. You can even use Snowflake's native query acceleration to speed up those Tableau dashboards without rebuilding them.
788778888: That's good to know. Our CEO keeps asking why the dashboards take so long to load during board meetings.
3444433: Yeah, that's the universal problem.
788778888: If we can make that faster, that alone would be a big win.
1212111: So just to summarize what I'm hearing—you're trying to centralize data from SQL Server and S3, reduce manual integration work, and improve dashboard performance.
788778888: Exactly.
1212111: Great. And on your side, who's leading the modernization project?
788778888: Our Director of Data Engineering, Priya. She's been pushing for more automation.
5556655: Nice. Would it make sense for us to loop her into a short technical session next week? We can walk through your current setup and show how Snowflake might streamline it.
788778888: Yeah, I can ask her. She's slammed this week, but next week should be fine.
1212111: Perfect. Why don't we pencil in Wednesday afternoon? I'll send over a placeholder invite, and we can adjust as needed.
788778888: Works for me.
3444433: Awesome. I can prep a quick architecture diagram showing what a phased migration might look like.
788778888: That would be great. Our leadership likes visuals.
1212111: Cool. And while we're at it, maybe we can talk through potential new use cases for Snowflake—like advanced forecasting or using AI models directly in Snowflake.
788778888: Yeah, that's interesting. We're actually starting to experiment with some predictive stuff for inventory optimization.
5556655: Oh, really? Are you doing that in-house?
788778888: Kind of. We've got a small data science team using Python, but right now, they're pulling data manually from different sources.
3444433: That's actually a perfect Snowflake use case. You could centralize the data and use Snowpark for Python so your data scientists can run their models right where the data lives—no exporting needed.
788778888: That would simplify things a lot.
1212111: Let's definitely explore that in the next session. I'll make a note.
788778888: Sounds good.
5556655: Out of curiosity, what kind of inventory models are you building?
788778888: We're trying to predict regional stock levels and reduce out-of-stocks. It's still early, but leadership's very interested in scaling it if we can get it working reliably.
3444433: Yeah, that's a huge opportunity area. Several Snowflake customers are doing similar forecasting directly in the platform.
788778888: I'd love to see some examples if you've got them.
1212111: Definitely. We can share a couple of anonymized case studies next week.
788778888: Great. Appreciate that.
3444433: So when we meet next week, we'll show how data from SQL Server and S3 can be brought in through Snowpipe or Fivetran, then modeled for your analysts.
788778888: That'd be great. Our exec team just wants something they can see in action.
5556655: We'll make it concrete. Maybe we could use a small supply chain dataset to demo the pipeline and a dashboard on top.
1212111: Perfect. And we'll show how resource monitors can alert you if compute costs exceed thresholds.
788778888: That's one of the biggest asks from finance. They want predictability.
3444433: Totally. We'll show a governance dashboard too—usage by team, warehouse, and project.
788778888: Excellent.
1212111: By the way, are there any blockers to expanding your Snowflake footprint?
788778888: Honestly, internal politics. Some folks are attached to Databricks for transformations.
5556655: That's fair. We can show how Snowflake and Databricks can coexist, or gradually migrate logic.
788778888: That'd help.
1212111: Another question—how's your data sharing with suppliers today?
788778888: Painful. We send CSVs over SFTP every week.
3444433: Yikes. You could publish that directly through Snowflake Data Sharing or even the Marketplace. Partners would query it live.
788778888: That would save us hours. But security would be a concern.
5556655: Definitely. We'll cover row-level and column-level security next week so you can control access precisely.
1212111: Great. We'll make that a key demo item.
788778888: Thanks. If this works, we might pilot it with two key suppliers this quarter.
1212111: Perfect. So quick recap.; We'll meet next Wednesday with Priya.; You'll share a small dataset for demo.; We'll show cost governance, live sharing, and Snowpark examples.
788778888: Sounds good.
3444433: And we'll include case studies and visuals for leadership.
5556655: I'll prep the example pipeline.
788778888: Appreciate it. This feels like real progress.
1212111: Same here. Let's make sure Priya's looped in by Monday.
788778888: Will do. Thanks, everyone.
$$,
'004G0005867qtHRAN',
'{"key_takeaway": "important takeaways here"}',
'2025-10-09'::DATE,
ARRAY_CONSTRUCT('sarim@snowflake.com', 'kirk@snowflake.com', 'howard@snowflake.com', 'seth@snowflake.com', 'john@companya.com'),
null
;

insert into ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic select
'CompanyA', 
'MEETING', 
'7578ghohjgt8rthljmvotur87947597935', 
'00184759847rG98TAU78', 
'Sarim from Snowflake, Kirk from Snowflake, Howard from Snowflake, Seth from Snowflake, John from CompanyA', 
'Followup Meeting',
$$
1212111: Hey, good to see you again. How's everything at CompanyA?
788778888: Pretty good overall. We've been juggling a few data projects—never a dull moment.
3444433: Sounds about right. Anything exciting going on?
788778888: We just kicked off an internal analytics revamp. Trying to consolidate reporting between marketing and supply chain.
5556655: That's awesome. Are you still running your main workloads on SQL Server and AWS?
788778888: Yep. Some of our analytics data sits in S3, and SQL Server still powers most of our transactional stuff. It works but it's clunky.
1212111: That's a common theme we hear. You mentioned before you were testing out Snowflake a bit—how's that going?
788778888: So far, so good. The dev team likes the separation of compute and storage. But we haven't fully migrated anything serious yet.
3444433: Totally makes sense. Starting small is smart. What's the biggest pain point right now?
788778888: Probably the delays between when data lands in S3 and when analysts can query it. Sometimes it's a full day behind.
5556655: Yeah, we see that often. You could automate ingestion with Snowpipe and have data available within minutes of landing.
788778888: That would be huge. Our marketing folks always complain that yesterday's numbers feel ancient.
1212111: We can show you how that looks. Also, have you played with any of the cost optimization settings yet—like auto-suspend or warehouse sizing?
788778888: Not really. Our team is still learning the ropes. I've heard Snowflake can get pricey if you don't monitor it carefully.
3444433: That's fair. The good news is you can set up resource monitors and alerts to automatically pause compute or notify you if budgets exceed a threshold.
788778888: Nice. Our finance team would love that. They've been nervous about runaway costs.
5556655: We could even build a small cost dashboard using Snowsight. That'd give visibility by department.
788778888: I like that idea.
1212111: Perfect. Maybe we can make that part of a quick follow-up session. How's next Thursday?
788778888: That should work.
3444433: Great. We'll walk through ingestion, cost governance, and show an example of your pipeline rebuilt in Snowflake.
788778888: That sounds like a plan.
5556655: Before we wrap, are there any new data initiatives you're considering?
788778888: Yeah, actually—we've been asked to look into demand forecasting. Right now, our analysts export data from three systems into Excel models. It's not sustainable.
3444433: That's a classic candidate for Snowpark. You can run your Python models right inside Snowflake—no need to move data around.
788778888: That would save so much time. We have one data scientist who spends hours just wrangling CSVs.
1212111: Let's include that in next week's session too. We can show how one of our retail customers does predictive modeling in Snowpark.
788778888: That would be great.
5556655: How big are your datasets right now, roughly?
788778888: Not massive—maybe two terabytes total. But it's growing fast as we add more IoT feeds from our distribution centers.
3444433: Oh, interesting—you're collecting IoT data?
788778888: Yeah, mostly temperature and uptime metrics from coolers and vending units. It's stored in S3 for now.
5556655: Perfect Snowflake use case again. You could land that data into a staging schema in Snowflake and join it directly with your sales data to get near-real-time insights.
788778888: That's the dream. Leadership wants visibility into downtime by region, but right now it takes a week to compile.
1212111: Let's aim to prototype that during the next session. Maybe start with one region's data as a proof of concept.
788778888: Yeah, I can send over a sample file early next week.
3444433: Awesome. And if you can loop in your data engineer too, we'll make it hands-on.
788778888: Sure thing.
5556655: Any concerns we should keep in mind before we dive in?
788778888: Just one—security reviews. Our IT team is cautious about anything that touches production data.
1212111: Totally understandable. We'll stick to anonymized datasets for the demo, and we can provide Snowflake's SOC 2 and FedRAMP docs if they need them.
788778888: That'd help a lot.
3444433: And Snowflake's governance features—row-level security, masking policies, object tagging—are all built in, so compliance is straightforward.
788778888: Good to know. I'll pass that along.
5556655: Thank you. Looking forward to showing you what's possible.
3444433: Same here. We'll get the invite out today.
1212111: Great. Have a good rest of the week.
788778888: You too. Talk soon.
$$,
'004G0005867qtHRAN',
'{"key_takeaway": "important takeaways here"}',
'2025-10-21'::DATE,
ARRAY_CONSTRUCT('sarim@snowflake.com', 'kirk@snowflake.com', 'howard@snowflake.com', 'seth@snowflake.com', 'john@companya.com'),
null
;

insert into ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic select
'CompanyA', 
'MEETING', 
'890uhjdklg9898t890fjkdjalgjjh88r88t8882223', 
'00184759847rG98TAU78', 
'Sarim from Snowflake, Kirk from Snowflake, Howard from Snowflake, Seth from Snowflake, John from CompanyA', 
'Predictive Inventory',
$$
1212111: Hey! Good to talk again. How are things going this week?
788778888: Pretty good—still chaotic, but that's just normal for us at this point.
3444433: Totally understand. Did you get a chance to look at the example architecture we sent over?
788778888: Yeah, Priya and I went through it. The Snowpark piece caught her attention.
1212111: Nice. We wanted to check in specifically on the predictive inventory project you mentioned last time. Any updates on what your data science team is running today?
788778888: They're still doing everything manually—pulling CSVs, cleaning them locally. It works for prototypes, but it's not scalable.
5556655: That's exactly where Snowpark helps. You can run all the Python transformations and XGBoost models directly in Snowflake, on the same compute your analytics team already uses. No exporting, no drift.
788778888: Yeah, that would simplify a lot. Priya's biggest complaint is managing environment consistency across people's laptops.
3444433: With Snowpark, the environment's standardized. And you can schedule the whole workflow with Tasks, so your forecasting jobs just run automatically.
788778888: That's appealing. Leadership keeps asking why the out-of-stock predictions vary depending on who ran the script.
1212111: Makes sense. For next steps, we can help you create a small Snowpark prototype—maybe start with one product line or one region.
788778888: I like that. If we can prove it out with a narrow scope, getting budget for the full rollout will be way easier.
5556655: Perfect. We'll bring an example during our next session so you can see the whole workflow end-to-end: ingest → feature engineering → training → inference → dashboard refresh.
788778888: Great. That'll help us socialize the idea internally.
1212111: Anything else on your radar that we should plan for?
788778888: Actually, yeah—our marketing team has been asking about something pretty different. They want an Agentic-style setup where they can ask natural-language questions about all the unstructured content we store in Snowflake. Things like campaign briefs, customer notes, call summaries.
3444433: Got it—natural language insights on unstructured data.
788778888: Exactly. They want to ask questions like “Why did engagement dip in Q3?” or “What themes are showing up in customer support notes?” and get answers without a ton of prep work.
1212111: That's doable. What are they currently using to do that work?
788778888: Manual hours. There really isn't a good system in place right now.
1212111: We can talk through some options using Cortex functions or retrieval-augmented workflows in Snowflake.
788778888: Perfect. Let's add that to the agenda for next week.
$$,
'004G0005867qtHRAN',
'{"key_takeaway": "important takeaways here"}',
'2025-11-01'::DATE,
ARRAY_CONSTRUCT('sarim@snowflake.com', 'kirk@snowflake.com', 'howard@snowflake.com', 'seth@snowflake.com', 'john@companya.com'),
null
;

insert into ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic select
'CompanyB', 
'MEETING', 
'12345969808jhgqpeuruzvn58t8ty7r8invat887', 
'002YTN87708FJbrdsd342', 
'Alex from Snowflake, Jordan from Snowflake, Priya from CompanyB', 
'Contract Status',
$$
1212222: Hi, this is Alex from Snowflake. How are you today?
3333333: Doing well, thanks. Excited to touch base.
9999999: Hey Alex, hey Jordan—this is Priya, CTO at CompanyB.
1212222: Great to hear! Anything specific you wanted to cover today?
9999999: Actually, yes. I just wanted to confirm that our legal team has reviewed and approved the contract. Everything is cleared on our side.
3333333: That's fantastic news. So signing will happen later this week?
9999999: Yep, we plan to get it signed by Friday.
1212222: Perfect. Once that's done, we can kick off onboarding and get your account fully set up.
9999999: Sounds good. Looking forward to it.
3333333: Excellent. We'll make sure all the paperwork and welcome materials are ready for you.
9999999: Thanks, appreciate it.
1212222: Alright, we'll let you go. Enjoy the rest of your day, Priya.
9999999: You too. Bye.
3333333: Bye!
$$,
'00789BNV8ouWWH',
'{"key_takeaway": "important takeaways here"}',
'2025-11-05'::DATE,
ARRAY_CONSTRUCT('alex@snowflake.com', 'jordan@snowflake.com', 'priya@companyb.com'),
null
;

insert into ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic 
select 'BrightWaveTech', 
'MEETING', 
'FJ38HJG92LKSJH38KJHDKJ23JH45KJH23', 
'003BRW2024-05-17-001', 
'Alice from Snowflake, Marcus from Snowflake, Elena from Snowflake, Victor from BrightWaveTech, Sara from BrightWaveTech', 
'Unified Data Governance and Real-Time Analytics',
$$
1001: Hi Victor and Sara, thanks for joining us today. How's everything at BrightWaveTech since we last spoke? 
1002: We've been busy, Alice. The security team finalized the audit results but flagged several inconsistencies across our data zones. 
1003: Understood. We've designed a governance framework that enforces policies at ingestion time and automatically tracks lineage. Would that address your main concerns? 
1004: That's exactly what we need. Right now we spend hours manually reconciling data and ensuring compliance for each source system. 
1005: With Snowflake's Object Tagging and Dynamic Data Masking, you can classify sensitive fields and hide them automatically for unauthorized roles. 
1002: That sounds promising. Can you walk us through a typical workflow? 
1003: Sure. When you load data into a staging table, you apply classification tags based on content patterns. Then, a masking policy triggers before any SELECT. Finally, automatically generated lineage dashboards show you upstream and downstream dependencies. 
1004: That real-time lineage view will save us a lot of headaches. How much overhead does it introduce? 
1001: Negligible. All enforcement happens at query compile time, and lineage metadata is captured asynchronously in system tables without impacting performance. 
1005: Great. Another topic: we want to enable real-time analytics on streaming IoT data from our sensor network. We're currently dumping raw files into S3 and using batch loads every four hours. 
1002: You can use Snowpipe Continuous Data Ingestion to stream JSON events directly into a table in seconds. Then, you can build materialized views for aggregated metrics and serve dashboards with sub-second refresh. 
1003: And if you want anomaly detection on those streams, you can integrate with Snowpark to run Python UDFs on incoming records. 
1004: That's exactly the capability we need. Especially if we can generate alerts when temperature or vibration thresholds exceed limits. 
1001: We can set up Task chains that evaluate each batch or micro-batch and push alerts via Notification Services to your Slack or PagerDuty channels. 
1005: Perfect. Finally, Sara has been investigating a way to manage cost allocation across teams and chargebacks. 
1002: We recommend using Resource Monitors combined with Usage Shares. You tag each warehouse or role by department, and Snowflake automatically allocates credits based on consumption. 
1004: Does that integrate with your Cost Governance Dashboard? 
1003: Absolutely. You get an out-of-the-box cost breakdown by project, user, or workload. You can even forecast next quarter's spend using historical patterns. 
1001: For next steps, we'll prepare a two-week proof of concept environment: governance policies, streaming ingestion, anomaly detection prototype, and cost dashboards. 
1005: That covers all our priorities. Thank you, everyone. Let's reconvene after the POC is live and review metrics and performance benchmarks. 
1002: Thanks, Alice and Marcus. Looking forward to it! 
$$,
'009BRW-OPP-0045678',
'{"key_takeaway": "important takeaways here"}',
'2025-11-05'::DATE,
ARRAY_CONSTRUCT('alice@snowflake.com', 'marcus@snowflake.com', 'elena@snowflake.com', 'victor@brightwavetech.com', 'sara@brightwavetech.com'),
null
;

insert into ${DATABASE}.${SCHEMA}.all_engagement_details_synthetic 
select
'FinNova',
'MEETING',
'XZ12MKL9OPQ34RST56UV78WX90YZAB12CD34EF56',
'004FNCV-2025-078',
'Alice from Snowflake, Raj from Snowflake, Emily from FinNova, Dave from FinNova',
'Snowflake Data Governance and ML Use Case Discussion',
$$
1001001001001: Hi everyone, thanks for joining today.; Let's start with a quick round of intros.; I'll pass to Raj first.;\\n2002002002002: Hello, I'm Raj on the Snowflake solutions engineering team, focused on data governance.;\\n1001001001001: Thanks, Raj. I'm Alice, Snowflake product manager for Data Science workloads.;\\n3003003003003: I'm Emily, head of analytics at FinNova, leading our fraud detection initiative.;\\n4004004004004: And I'm Dave, data architect at FinNova, working on our compliance pipelines.;\\n1001001001001: Great. The goal today is to map out how Snowflake can support your data privacy rules and also power the ML models you mentioned.;\\n2002002002002: Precisely. We can use dynamic data masking and row-access policies to enforce GDPR and CCPA. Then share curated datasets with your ML team through secure data sharing.;\\n3003003003003: That sounds promising. We need to ensure personally identifiable information is masked before any model training.;\\n4004004004004: Also, can we schedule automatic policy audits? We must generate compliance reports monthly for our regulators.;\\n2002002002002: Yes, with Snowflake's Access History and Tag-Based masking, you can track usage and produce reports via INFORMATION_SCHEMA views.;\\n1001001001001: On the ML side, you can leverage Snowpark for Python to build feature pipelines directly inside Snowflake. No data egress needed.;\\n3003003003003: Excellent. That would simplify our architecture and cut costs. Can you share a sample Python notebook?;\\n2002002002002: Absolutely. I'll drop a link to our GitHub repo after the call.;\\n4004004004004: One more thing: we have budget constraints. Do you have any best practices for cost control?;\\n1001001001001: Yes, you can set Resource Monitors on your warehouses and use auto-suspend and scaling policies. We'll share a guide.\\n3003003003003: Perfect. Let's recap next steps.;\\n1001001001001: Raj will send over the masking examples and Python notebook link.;\\n2002002002002: I'll also include our compliance reporting SQL templates.;\\n1001001001001: Emily and Dave, please provide sample PII schemas you'd like to mask by Friday.;\\n3003003003003: Will do.;\\n4004004004004: Thanks everyone.;\\n1001001001001: Thanks, talk soon.;\\n2002002002002: Goodbye!.
$$,
'007FNOVA00012345',
'{"key_takeaway": "important takeaways here"}',
'2025-11-10'::DATE,
ARRAY_CONSTRUCT('alice@snowflake.com','raj@snowflake.com','emily@finnova.com','dave@finnova.com'),
null
;