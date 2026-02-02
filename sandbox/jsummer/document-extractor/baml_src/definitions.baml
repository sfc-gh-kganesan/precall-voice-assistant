class Date {
    day int @description("The 2-digit day of the signature date")
    month int @description("The 2-digit month of the signature date")
    year int @description("The full 4-digit year of the signature date")
}

class Company {
  name string
  signature_date Date
}

class ContractMetadata {
    companies Company[]
}

