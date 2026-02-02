from baml_client.sync_client import b
from baml_client.types import ContractMetadata


def extract_metadata(content: str) -> ContractMetadata: 
    response = b.ExtractMetadata(content)
    return response
                    