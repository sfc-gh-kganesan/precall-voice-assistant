import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { Search, X, Filter } from "lucide-react";

interface InvoiceFiltersProps {
  groupBy: string;
  onGroupByChange: (value: string) => void;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  onClearFilters: () => void;
}

export function InvoiceFilters({
  groupBy,
  onGroupByChange,
  searchTerm,
  onSearchChange,
  onClearFilters
}: InvoiceFiltersProps) {
  return (
    <div className="mb-8 p-6 border border-[var(--snowflake-blue)]/20 rounded-xl bg-gradient-to-r from-[var(--snowflake-light-blue)]/40 to-blue-50/40 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-[var(--snowflake-blue)]" />
        <h3 className="text-[var(--snowflake-blue)]">Filter & Search</h3>
      </div>
      
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Label htmlFor="search" className="text-sm mb-2 block">Search Invoices</Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              id="search"
              placeholder="Search by invoice #, vendor, lift ticket #, or PO #..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-9 border-[var(--snowflake-blue)]/30 focus:border-[var(--snowflake-blue)] focus:ring-[var(--snowflake-blue)]"
            />
          </div>
        </div>

        <div className="min-w-[200px]">
          <Label htmlFor="groupBy" className="text-sm mb-2 block">Group By</Label>
          <Select value={groupBy} onValueChange={onGroupByChange}>
            <SelectTrigger 
              id="groupBy"
              className="border-[var(--snowflake-blue)]/30 focus:border-[var(--snowflake-blue)] focus:ring-[var(--snowflake-blue)]"
            >
              <SelectValue placeholder="Select grouping" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No Grouping</SelectItem>
              <SelectItem value="liftTicket">Lift Ticket #</SelectItem>
              <SelectItem value="purchaseOrder">Purchase Order #</SelectItem>
              <SelectItem value="vendor">Vendor</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-end">
          <Button
            variant="outline"
            onClick={onClearFilters}
            className="flex items-center gap-2 border-[var(--snowflake-blue)]/50 text-[var(--snowflake-blue)] hover:bg-[var(--snowflake-blue)] hover:text-white"
          >
            <X className="w-4 h-4" />
            Clear
          </Button>
        </div>
      </div>
    </div>
  );
}