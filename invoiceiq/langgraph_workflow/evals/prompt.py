JUDGE_PROMPT = """
You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:

<Rubric>
  Assign a score of 0 or 1 based on the following criteria:
  - 1: The AI Extract Metadata matches or is semantically similar to the corresponding information in the reference output
  - 0: The AI Extract Metadata does not match or is not semantically similar to the corresponding information in the reference output
</Rubric>

<Additional Information>
You may ignore the following fields when evaluating the score:
- decisions regarding approval or rejection of the invoice
- reasoning for the decision
- unrelated input information including the invoice ID, target table, relative path, and stage name
</Additional Information>

<input>
{inputs}
</input>

<output>
{outputs}
</output>

<reference_outputs>
{reference_outputs}
</reference_outputs>
"""