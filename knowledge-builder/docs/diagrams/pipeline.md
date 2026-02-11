# Knowledge Builder Pipeline

## Complete Pipeline Diagram

```mermaid
%%{ init: { 'flowchart': { 'curve': 'basis' } } }%%
flowchart TB
    subgraph INGESTION["Data Ingestion"]
        CSV1[kb_knowledge.csv] --> STAGE[(KNOWLEDGE Stage)]
        CSV2[synthetic_pairs.csv] --> STAGE
        STAGE --> KB_KNOWLEDGE[(KB_KNOWLEDGE)]
        STAGE --> SYNTHETIC_PAIRS[(SYNTHETIC_PAIRS)]
        SEED[Seed Data] --> GOLDEN_PAIRS[(GOLDEN_PAIRS)]
    end

    subgraph PROCESSING["Text Processing"]
        KB_KNOWLEDGE --> STRIP[Strip HTML Tags]
        STRIP --> SPLIT[SPLIT_TEXT_RECURSIVE_CHARACTER<br/>1800 chars / 300 overlap]
        SPLIT --> KB_CHUNKS[(KB_CHUNKS)]
    end

    subgraph SEARCH["Cortex Search Service"]
        KB_CHUNKS --> KB_SEARCH{{KB_SEARCH<br/>Cortex Search Service}}
        KB_SEARCH <--> STATE_MGR[State Manager<br/>Search Config]
    end

    subgraph EVALUATION["Search & Evaluation Pipeline"]
        GOLDEN_PAIRS --> TASK_ROOT[SEARCH_ON_PAIRS_ROOT<br/>Task DAG]
        SYNTHETIC_PAIRS --> TASK_ROOT
        TASK_ROOT --> TASK_GOLDEN[SEARCH_ON_GOLDEN_PAIRS]
        TASK_ROOT --> TASK_SYNTH[SEARCH_ON_SYNTHETIC_PAIRS]
        TASK_GOLDEN --> KB_SEARCH
        TASK_SYNTH --> KB_SEARCH
        STATE_MGR -.-> SEARCH_QUERIES
        KB_SEARCH --> SEARCH_QUERIES[(SEARCH_QUERIES)]
        SEARCH_QUERIES --> EVAL_PROC[EVALUATE_CONTEXT_RELEVANCE]
        EVAL_STATE[State Manager<br/>Eval Config] <--> EVAL_PROC
        EVAL_PROC --> EVALUATION_RESULTS[(EVALUATION_RESULTS)]
        EVAL_STATE -.-> EVALUATION_RESULTS
    end

    subgraph UI["Streamlit Applications"]
        FEEDBACK_APP[Feedback App]
        TAXONOMY_APP[Taxonomy App]
        
        SEARCH_QUERIES --> FEEDBACK_APP
        EVALUATION_RESULTS --> FEEDBACK_APP
        FEEDBACK_APP --> SEARCH_FEEDBACK[(SEARCH_FEEDBACK)]
        
        SYNTHETIC_PAIRS --> TAXONOMY_APP
        EVALUATION_RESULTS --> TAXONOMY_APP
        SEARCH_QUERIES --> TAXONOMY_APP
    end

    style INGESTION fill:#29B5E8,color:#FFFFFF
    style PROCESSING fill:#FF9F36,color:#FFFFFF
    style SEARCH fill:#75CDD7,color:#5B5B5B
    style EVALUATION fill:#D45B90,color:#FFFFFF
    style UI fill:#7254A3,color:#FFFFFF
```

## Pipeline Stages

### 1. Data Ingestion
- **kb_knowledge.csv**: ServiceNow knowledge articles exported to CSV
- **synthetic_pairs.csv**: LLM-generated query/resolution pairs with L1-L4 taxonomy tags
- **Seed Data**: Curated golden pairs for baseline testing

### 2. Text Processing
- Strip HTML tags using regex
- Split text using `SPLIT_TEXT_RECURSIVE_CHARACTER` (1800 chars, 300 overlap)
- Output stored in `KB_CHUNKS` table with composite key (KB_SYS_ID, CHUNK_INDEX)

### 3. Cortex Search Service
- `KB_SEARCH` service indexes `CHUNK_TEXT` column
- Attributes: KB_SYS_ID, KB_NUMBER, KNOWLEDGE_BASE, etc.
- Target lag: 1 hour
- **State Manager (Search Config)**: Tracks search service configuration for A/B testing

### 4. Search & Evaluation Pipeline
- Task DAG (`SEARCH_ON_PAIRS_ROOT`) orchestrates parallel search execution
- Results stored in `SEARCH_QUERIES` with INPUT_TYPE (GOLDEN_PAIR or SYNTHETIC_PAIR)
- Context relevance evaluation with chain-of-thought reasoning
- Scores and reasoning stored in `EVALUATION_RESULTS`
- **State Manager (Eval Config)**: Tracks evaluation parameters (framework, model, prompts, thresholds) for A/B testing

### 5. Streamlit Applications
- **Feedback App**: Quality coverage, evaluation, playground, feedback collection, EDA
- **Taxonomy App**: Sunburst visualization, KPI metrics, KB leaderboard, gap analysis
