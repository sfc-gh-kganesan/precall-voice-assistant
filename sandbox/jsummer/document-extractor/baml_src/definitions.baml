enum PartyRole {
    Buyer
    Seller
    Operator
    Other
}

enum ContractTermCategory {
      Payment
      Delivery
      Quality
      Pricing
      FeeOrPenalty
      Reporting
      CreditOrSecurity
      Operational
      ForceMajeureOrException
      Other
}

class Citation {
    source_text string @description("The text from the document")
    bounding_box_dimensions string? @description(#"The dimensions of the bounding box of the relevant text in the document.
    If the relevant sections span multiple bounding boxes, the dimensions should encapsulate the entire relevant area. 
    For example, if the relevant text spans from the top of the first bounding box to the bottom of the second bounding box, the dimensions should be the union of the two bounding boxes.
    "#) 
}

class Date {
    day int @description("The 2-digit day of the signature date")
    month int @description("The 2-digit month of the signature date")
    year int @description("The full 4-digit year of the signature date")
    citation Citation @description("The citations from the document to the date")
}

class Party {
  name string @description("Legal or business name of a party in the contract")
  signature_date Date @description("The signature date of the party")
  role PartyRole @description("The role of the party in the contract")
  citation Citation @description("The citation from the document to the party")
}

class ContractMetadata {
    document_id string @description("The unique identifier for the document if available. Otherwise, create a unique identifier based on the document content.")
    document_title string @description("The title of the document if available. Otherwise, create a short title based on the document content.")
    document_date Date? @description("The date of the document, if provided")
    effective_start Date @description("The effective start date of the contract")
    effective_end Date @description("The effective end date of the contract")
    parties Party[]
    terms ContractTerm[]
}

class ContractTerm {
    title string @description("The title of the term")
    summary string @description("The summary of the term")
    category ContractTermCategory @description("The category of the term")
    citation Citation @description("The citation from the document to the term")
}