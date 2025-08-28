# Invoice IQ

A beautiful and functional React TypeScript dashboard for automated invoice processing. Built for accounts payable teams in large enterprise organizations to track and manage invoice processing workflows.

## Features

- **Auto-Processing Metrics**: View percentage of invoices processed automatically without human intervention
- **Key Performance Indicators**: Track total invoices, pending exceptions, and average processing time
- **Exception Management**: Review and manage pending invoice exceptions requiring human attention
- **Action Items**: Track important tasks like uploads, reviews, assignments, and reports
- **Beautiful UI**: Built with Shadcn UI components and Tailwind CSS for a modern, professional look
- **Responsive Design**: Optimized for desktop and tablet use

## Tech Stack

- **Frontend**: React 19 + TypeScript
- **Build Tool**: Vite
- **UI Components**: Shadcn UI
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js (version 18 or higher)
- npm or yarn

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

### Running the Application

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Open your browser and navigate to `http://localhost:5173`

### Building for Production

1. Build the application:
   ```bash
   npm run build
   ```

2. Preview the production build:
   ```bash
   npm run preview
   ```

## Project Structure

```
src/
├── components/
│   ├── ui/               # Shadcn UI components
│   └── Dashboard.tsx     # Main dashboard component
├── data/
│   └── mockData.ts      # Sample data for demonstration
├── types/
│   └── index.ts         # TypeScript type definitions
├── App.tsx              # Main app component
├── main.tsx            # App entry point
└── index.css           # Global styles with Tailwind
```

## Dashboard Overview

The dashboard displays:

1. **Metrics Cards**: Auto-processed rate, total invoices, pending exceptions, average processing time
2. **Processing Breakdown**: Visual breakdown of auto-processed, manually reviewed, and rejected invoices
3. **Action Items**: Priority tasks requiring attention
4. **Exceptions Table**: Detailed list of pending exceptions with vendor information, amounts, and assignment status

## Sample Data

The application includes comprehensive mock data demonstrating:
- Various invoice exception types (missing PO, mismatches, duplicates, insufficient funds)
- Priority levels (high, medium, low)
- Assignment status and processing workflows
- Realistic financial amounts and vendor names

## Future Enhancements

This UI is ready for integration with real backend services for:
- Live data fetching
- User authentication
- Real-time updates
- Assignment management
- Reporting functionality
