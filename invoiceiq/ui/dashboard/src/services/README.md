# React Query Hooks for InvoiceIQ API

This directory contains the React Query implementation for the InvoiceIQ API.

## Files

- **types.ts**: TypeScript type definitions for API requests and responses
- **queryClient.ts**: React Query client configuration
- **hooks.ts**: Custom React Query hooks for API calls
- **api.ts**: Legacy API functions (deprecated, kept for backward compatibility)
- **mapper.ts**: Data mapping utilities

## Usage

### Setup

The app is already wrapped with `QueryClientProvider` in `main.tsx`:

```tsx
import { QueryClientProvider } from 'react-query';
import { queryClient } from './services/queryClient';

<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

### Query Hooks

#### Fetch Invoice Statistics

```tsx
import { useInvoiceStats } from './services/hooks';

function MyComponent() {
  const { data, isLoading, error } = useInvoiceStats();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <p>Total: {data?.total}</p>
      <p>Approved: {data?.approved}</p>
      <p>Pending: {data?.pending}</p>
      <p>Rejected: {data?.rejected}</p>
    </div>
  );
}
```

#### Fetch All Invoices

```tsx
import { useAllInvoices } from './services/hooks';

function MyComponent() {
  const { data, isLoading, error } = useAllInvoices(100);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h3>Approved ({data?.approved_count})</h3>
      {data?.approved.map(invoice => <div key={invoice.id}>{invoice.vendor_name}</div>)}
      
      <h3>Pending ({data?.pending_count})</h3>
      {data?.pending.map(invoice => <div key={invoice.id}>{invoice.vendor_name}</div>)}
      
      <h3>Rejected ({data?.rejected_count})</h3>
      {data?.rejected.map(invoice => <div key={invoice.id}>{invoice.vendor_name}</div>)}
    </div>
  );
}
```

#### Fetch Invoices with Filters

```tsx
import { useInvoices } from './services/hooks';

function MyComponent() {
  const [status, setStatus] = useState('pending');
  const { data, isLoading, error } = useInvoices(status, 100, 0);

  // Data will automatically refetch when status changes
  return (
    <div>
      <select value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="approved">Approved</option>
        <option value="pending">Pending</option>
        <option value="rejected">Rejected</option>
      </select>
      
      {isLoading && <div>Loading...</div>}
      {error && <div>Error: {error.message}</div>}
      {data?.invoices.map(invoice => <div key={invoice.id}>{invoice.vendor_name}</div>)}
    </div>
  );
}
```

#### Search Invoices

```tsx
import { useSearchInvoices } from './services/hooks';

function MyComponent() {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchBy, setSearchBy] = useState<'liftTicket' | 'purchaseOrder'>('liftTicket');
  
  const { data, isLoading, error } = useSearchInvoices(
    searchBy,
    searchTerm,
    1000,
    0
  );

  return (
    <div>
      <select value={searchBy} onChange={(e) => setSearchBy(e.target.value as 'liftTicket' | 'purchaseOrder')}>
        <option value="liftTicket">Lift Ticket #</option>
        <option value="purchaseOrder">Purchase Order #</option>
      </select>
      
      <input
        type="text"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        placeholder="Search..."
      />
      
      {isLoading && <div>Loading...</div>}
      {error && <div>Error: {error.message}</div>}
      {data?.invoices.map(invoice => <div key={invoice.id}>{invoice.vendor_name}</div>)}
    </div>
  );
}
```

### Mutation Hooks

#### Update Invoice Status

```tsx
import { useUpdateInvoiceStatus } from './services/hooks';
import { toast } from 'sonner';

function MyComponent() {
  const updateStatus = useUpdateInvoiceStatus({
    onSuccess: (data) => {
      toast.success(`${data.updated_count} invoice(s) updated`);
    },
    onError: (error) => {
      toast.error(`Error: ${error.message}`);
    },
  });

  const handleApprove = (ticketNumbers: string[]) => {
    updateStatus.mutate({
      ticketNumbers,
      status: 'approved',
    });
  };

  return (
    <button 
      onClick={() => handleApprove(['TICKET-123'])}
      disabled={updateStatus.isLoading}
    >
      {updateStatus.isLoading ? 'Updating...' : 'Approve'}
    </button>
  );
}
```

#### Update Invoice Fields

```tsx
import { useUpdateInvoiceFields } from './services/hooks';
import { toast } from 'sonner';

function MyComponent() {
  const updateFields = useUpdateInvoiceFields({
    onSuccess: () => {
      toast.success('Invoice updated successfully');
    },
    onError: (error) => {
      toast.error(`Error: ${error.message}`);
    },
  });

  const handleUpdate = (ticketNumber: string) => {
    updateFields.mutate({
      ticketNumber,
      fields: {
        vendor_name: 'New Vendor Name',
        total_amount: '1000.00',
      },
    });
  };

  return (
    <button 
      onClick={() => handleUpdate('TICKET-123')}
      disabled={updateFields.isLoading}
    >
      {updateFields.isLoading ? 'Updating...' : 'Update Fields'}
    </button>
  );
}
```

#### Reprocess Invoice

```tsx
import { useReprocessInvoice } from './services/hooks';
import { toast } from 'sonner';

function MyComponent() {
  const reprocess = useReprocessInvoice({
    onSuccess: (data) => {
      toast.success(data.message);
    },
    onError: (error) => {
      toast.error(`Error: ${error.message}`);
    },
  });

  const handleReprocess = (ticketNumber: string) => {
    reprocess.mutate({ ticketNumber });
  };

  return (
    <button 
      onClick={() => handleReprocess('TICKET-123')}
      disabled={reprocess.isLoading}
    >
      {reprocess.isLoading ? 'Reprocessing...' : 'Reprocess with AI'}
    </button>
  );
}
```

### Utility Functions

```tsx
import { getViewPdfUrl, getDownloadPdfUrl, downloadPdf } from './services/hooks';

function MyComponent({ ticketNumber }: { ticketNumber: string }) {
  const handleDownload = async () => {
    try {
      await downloadPdf(ticketNumber);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div>
      {/* View PDF inline */}
      <iframe src={getViewPdfUrl(ticketNumber)} />
      
      {/* Download PDF link */}
      <a href={getDownloadPdfUrl(ticketNumber)} download>
        Download PDF
      </a>
      
      {/* Download PDF button */}
      <button onClick={handleDownload}>
        Download PDF
      </button>
    </div>
  );
}
```

## Advanced Usage

### Refetching Data

```tsx
import { useInvoiceStats } from './services/hooks';

function MyComponent() {
  const { data, refetch } = useInvoiceStats();

  return (
    <div>
      <button onClick={() => refetch()}>
        Refresh Stats
      </button>
    </div>
  );
}
```

### Manual Cache Invalidation

```tsx
import { useQueryClient } from 'react-query';
import { queryKeys } from './services/hooks';

function MyComponent() {
  const queryClient = useQueryClient();

  const handleRefreshAll = () => {
    // Invalidate all invoice-related queries
    queryClient.invalidateQueries(queryKeys.invoiceStats);
    queryClient.invalidateQueries(queryKeys.allInvoices());
    queryClient.invalidateQueries(queryKeys.invoices());
  };

  return (
    <button onClick={handleRefreshAll}>
      Refresh All Data
    </button>
  );
}
```

### Optimistic Updates

The mutation hooks automatically invalidate related queries on success. For more complex optimistic updates, you can use the `onMutate` callback:

```tsx
import { useUpdateInvoiceStatus } from './services/hooks';
import { useQueryClient } from 'react-query';

function MyComponent() {
  const queryClient = useQueryClient();
  
  const updateStatus = useUpdateInvoiceStatus({
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries(queryKeys.allInvoices());
      
      // Snapshot current value
      const previousInvoices = queryClient.getQueryData(queryKeys.allInvoices());
      
      // Optimistically update
      // ... your optimistic update logic here
      
      return { previousInvoices };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousInvoices) {
        queryClient.setQueryData(queryKeys.allInvoices(), context.previousInvoices);
      }
    },
  });

  return <div>...</div>;
}
```

## Migration Guide

### Before (using api.ts)

```tsx
import { fetchInvoiceStats } from './services/api';

function MyComponent() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function loadStats() {
      try {
        const data = await fetchInvoiceStats();
        setStats(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return <div>{loading ? 'Loading...' : stats?.total}</div>;
}
```

### After (using hooks)

```tsx
import { useInvoiceStats } from './services/hooks';

function MyComponent() {
  const { data: stats, isLoading } = useInvoiceStats();

  return <div>{isLoading ? 'Loading...' : stats?.total}</div>;
}
```

## Benefits

- **Automatic caching**: Data is cached and reused across components
- **Automatic refetching**: Data is automatically refetched when it becomes stale
- **Request deduplication**: Multiple components requesting the same data will only trigger one API call
- **Automatic error handling**: Built-in error states and retry logic
- **Optimistic updates**: Update UI immediately before API response
- **Cache invalidation**: Mutations automatically invalidate related queries
- **TypeScript support**: Full type safety with IntelliSense
- **Developer tools**: React Query DevTools for debugging (can be added separately)

