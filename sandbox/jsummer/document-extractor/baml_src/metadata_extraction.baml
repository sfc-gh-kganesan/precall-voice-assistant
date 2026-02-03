function BaseExtract(content: string) -> ContractMetadata {
  client "Cortex"
  prompt #"
    You are an expert contract-analysis system.
    Your task is to extract the metadata and contractual termsfrom contracts.

    Here is the contract:
    {{ content }}

    Your output should follow the following JSON format:
    {{ ctx.output_format }}
  "#
}

function ContentBlocksExtract(content_string: string, content_blocks: string) -> ContractMetadata {
  // This function receives teh content string and block-based bounding boxes
  client "Cortex"
  prompt #"
    You are an expert contract-analysis system.
    Your task is to extract the metadata and contractual termsfrom contracts.

    Here is the contract content:
    {{ content_string }}

    Here are the bounding blocks of the content:
    {{ content_blocks }}

    Your output should follow the following JSON format:
    {{ ctx.output_format }}
  "#
}