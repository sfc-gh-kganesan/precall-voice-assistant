from baml_client.sync_client import b
from baml_client.types import ContractMetadata
import json


def base_extract(content: str) -> ContractMetadata: 
    response = b.BaseExtract(content)
    return response
                    
def content_blocks_extract(content: dict) -> ContractMetadata:
    response = b.ContentBlocksExtract(content["full_text"], json.dumps(content["blocks"]))
    return response