function ExtractMetadata(content: string) -> ContractMetadata {
  client "Cortex" // Set OPENAI_API_KEY to use this client.
  prompt #"
    Extract the metadata from this contract:
    {{ content }}

    {{ ctx.output_format }}
  "#
}