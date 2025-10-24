import { Filter, Search, X } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface InvoiceFiltersProps {
  searchBy: string;
  onSearchByChange: (value: string) => void;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
  onClearFilters: () => void;
}

export function InvoiceFilters({
  searchBy,
  onSearchByChange,
  searchTerm,
  onSearchChange,
  onSearch,
  onClearFilters,
}: InvoiceFiltersProps) {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <div className="mb-8 p-6 border border-[var(--snowflake-blue)]/20 rounded-xl bg-gradient-to-r from-[var(--snowflake-light-blue)]/40 to-blue-50/40 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-[var(--snowflake-blue)]" />
        <h3 className="text-[var(--snowflake-blue)]">Search Invoices</h3>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="min-w-[220px]">
          <Label htmlFor="searchBy" className="text-sm mb-2 block">
            Search By
          </Label>
          <Select value={searchBy} onValueChange={onSearchByChange}>
            <SelectTrigger
              id="searchBy"
              className="border-[var(--snowflake-blue)]/30 focus:border-[var(--snowflake-blue)] focus:ring-[var(--snowflake-blue)]"
            >
              <SelectValue placeholder="Select field" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="liftTicket">Lift Ticket #</SelectItem>
              <SelectItem value="purchaseOrder">Purchase Order #</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1">
          <Label htmlFor="search" className="text-sm mb-2 block">
            Search Term
          </Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              id="search"
              placeholder={`Enter ${searchBy === 'liftTicket' ? 'Lift Ticket #' : 'Purchase Order #'}...`}
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyPress={handleKeyPress}
              className="pl-9 border-[var(--snowflake-blue)]/30 focus:border-[var(--snowflake-blue)] focus:ring-[var(--snowflake-blue)]"
            />
          </div>
        </div>

        <div className="flex items-end gap-2">
          <Button
            onClick={onSearch}
            className="flex items-center gap-2 bg-[var(--snowflake-blue)] hover:bg-[var(--snowflake-blue)]/90 text-white"
          >
            <Search className="w-4 h-4" />
            Search
          </Button>
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
