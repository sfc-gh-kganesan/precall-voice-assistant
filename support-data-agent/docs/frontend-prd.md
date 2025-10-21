# Product Requirements Document (PRD)
## Support Intelligence Platform

### Version 1.1
### Date: October 2024
### Last Updated: December 2024

---

## 1. Executive Summary

The Support Intelligence Platform is a React/Next.js web application that empowers Product Managers and Customer Support teams to extract actionable insights from support tickets and call transcripts. The platform leverages Snowflake as its data backend and provides an intuitive interface for data configuration and analytics visualization.

### Key Features:
- **Admin Setup Module**: Sequential workflow for configuring data sources and field mappings
- **Analytics Dashboard**: Pre-calculated KPIs with period comparisons focused on product and topic intelligence
- **AI Chat Assistant**: Natural language interface for querying any data in the system
- **Snowflake Integration**: Direct connection to Snowflake tables with custom taxonomy generation
- **Dark Mode UI**: Modern dark theme interface optimized for extended use

---

## 2. Product Overview

### Vision
Enable data-driven decision making by transforming unstructured support data into structured, actionable intelligence.

### Goals
1. Reduce time to insight from support data by 80%
2. Automate topic and product classification using AI/ML
3. Provide self-service analytics for non-technical users
4. Enable proactive product improvements based on support trends

### Non-Goals (v1.0)
- Real-time ticket processing
- Multi-tenant architecture
- Mobile application
- Direct CRM integrations

---

## 3. User Personas

### Primary Personas

#### 1. Admin User (Data Administrator)
- **Role**: IT/Data team member
- **Goals**: Configure data sources, set up field mappings, ensure data quality
- **Pain Points**: Manual data preparation, complex ETL processes
- **Technical Level**: High

#### 2. Product Manager
- **Role**: Product strategy and roadmap owner
- **Goals**: Identify feature requests, bug patterns, user pain points
- **Pain Points**: Scattered insights, manual report generation
- **Technical Level**: Medium

#### 3. Customer Support Operations Manager
- **Role**: Support team leadership
- **Goals**: Track team performance, identify training needs, improve response times
- **Pain Points**: Lack of visibility into support trends
- **Technical Level**: Low-Medium

---

## 4. User Flows

### 4.1 Admin Setup Flow

```
1. Select Data Source → 2. Configure Mappings → 3. Generate Fields → 4. Save Configuration → 5. Trigger Analytics
```
*Note: No authentication required for MVP*

#### Detailed Steps:

**Step 1: Data Source Selection**
- Admin navigates to Setup module
- Views list of available Snowflake databases
- Selects database and table(s) containing support data
- System validates connection and displays sample data (25-50 rows max)

**Step 2: Field Mapping Configuration**
- System displays required fields: timestamp, topic, product, feature
- Admin maps existing columns or configures generation rules
- For generated fields, admin selects:
  - Source column (e.g., ticket_body for topic extraction)
  - Generation method (LLM extraction, regex, lookup)
  - Validation rules

**Step 3: Field Generation Execution**
- Admin reviews mapping configuration
- Clicks "Generate Fields" to execute
- System shows progress bar only (no time estimates)
- Preview of generated data displayed

**Step 4: Save Configuration**
- Admin reviews generated fields
- Selects destination table name
- Confirms save operation
- System creates new table with enhanced fields

**Step 5: Analytics Initialization**
- System automatically triggers KPI calculation
- Creates materialized views for performance
- Notifies admin when analytics are ready

### 4.2 Analytics Dashboard Flow

```
1. Dashboard Overview → 2. Filter/Drill Down → 3. Export/Share → 4. AI Chat (available throughout)
```
*Note: No authentication required for MVP*

### 4.3 AI Chat Assistant Flow

```
1. Click Chat Icon → 2. Type Question → 3. View Response → 4. Follow-up Questions → 5. Minimize/Close
```

#### Chat Interaction Examples:
- "Show me resolution rates for Product X last month"
- "What are the top issues affecting customers this week?"
- "Compare support volume between Q3 and Q4"
- "Which features have the most bug reports?"

---

## 5. Feature Requirements

### 5.1 Admin Setup Module

#### 5.1.1 Data Source Selection
- **Snowflake Connection Browser**
  - Tree view of databases/schemas/tables
  - Search functionality
  - Preview panel showing table schema and sample rows
  - Multi-select for joining tables

#### 5.1.2 Field Mapping Interface
- **Visual Mapping Builder**
  - Drag-and-drop interface
  - Required fields highlighted
  - Auto-suggestion based on column names
  - Custom function builder for complex mappings

#### 5.1.3 Field Generation Engine
- **Processing Options**
  - Batch size configuration
  - Sampling options for testing
  - Real-time progress tracking
  - Error handling and retry logic

#### 5.1.4 Configuration Management
- **Save/Load Configurations**
  - Named configurations
  - Version history
  - Rollback capability
  - Configuration templates

### 5.2 Analytics Dashboard

#### 5.2.1 Overview Dashboard
- **Key Metrics Grid** (all metrics pre-calculated by backend)
  - Total cases (current period vs previous period)
  - Average case life/duration (current period vs previous period)
  - Resolution rate (current period vs previous period)
    - Formula: (Cases with status='closed') / (Total cases created) × 100
  - Period selector: Default shows latest week vs previous week
  - Top products/features by volume
- **KPI Card Design**:
  - Large metric value
  - Metric label below
  - Small green/red arrow indicating change direction
  - No drill-down functionality in MVP

#### 5.2.2 Product Intelligence View
- **Product-Centric KPIs** (backend-calculated, frontend displays only)
  - Average cases by product (with period comparison)
  - Average case life by product (with period comparison)
  - Resolution rate by product (with period comparison)
  - Product hierarchy: Category → Product → Feature
  - Issues by product
  - Feature requests by product
  - Bug reports trend

#### 5.2.3 Topic Intelligence View
- **Topic-Centric KPIs** (backend-calculated, frontend displays only)
  - Average cases by topic (with period comparison)
  - Average case life by topic (with period comparison)
  - Resolution rate by topic (with period comparison)
  - Emerging topics
  - Topic volume over time
  - Topic sentiment analysis

#### 5.2.4 Filtering & Interactivity
- **Global Filters**
  - Date range picker
  - Product multi-select
  - Topic search
  - Customer segment filters
- **Table Specifications**
  - Pagination: 25 rows default
  - Basic client-side sorting on columns
  - No infinite scroll
  - Horizontal scroll on mobile devices

### 5.3 AI Chat Assistant

#### 5.3.1 Chat Interface
- **Floating Chat Button**
  - Position: Bottom right corner of screen
  - Always visible across all pages
  - Minimize/maximize functionality
  - Hidden on mobile devices (<768px)

#### 5.3.2 Chat Window
- **Conversation Interface**
  - Dark theme consistent with overall UI
  - Message bubbles (user vs AI)
  - Typing indicator: 3 dots animation for 1-2 seconds before AI response
  - Timestamp on messages
  - Auto-scroll to latest message
  - Welcome message: "Hi! Ask me anything about your support data."
  - No message persistence between page refreshes
  - Character limit: 500 characters per message

#### 5.3.3 Chat Capabilities
- **Natural Language Queries**
  - Query any data in the system
  - Context-aware responses
  - Support for follow-up questions
  - Query history within session

#### 5.3.4 Response Types
- **AI Responses Include**
  - Text explanations
  - Relevant metrics
  - Suggestions for next queries
  - References to specific data points

---

## 6. User Interface Design

### 6.1 Design Principles
- **Dark Mode First**: Pure black background (#000000) with high contrast
- **Clarity**: Clear visual hierarchy and intuitive navigation
- **Efficiency**: Minimize clicks to insight
- **Consistency**: Unified design language across modules
- **Accessibility**: WCAG 2.1 AA compliance with dark mode considerations

### 6.2 Color Palette
- **Primary Background**: #000000 (Pure Black)
- **Secondary Background**: #0A0A0A (Near Black)
- **Primary Accent**: #29B5E8 (Snowflake Blue)
- **Secondary Accent**: #1E88E5 (Darker Blue)
- **Text Primary**: #FFFFFF (White)
- **Text Secondary**: #B0B0B0 (Light Gray)
- **Success**: #4CAF50
- **Warning**: #FF9800
- **Error**: #F44336

### 6.3 Component Library

#### Core Components:
1. **DataSourceSelector**
   - Snowflake database/table browser
   - Search and filter capabilities
   - Preview panel

2. **FieldMapper**
   - Drag-and-drop mapping interface
   - Validation indicators
   - Custom function editor

3. **ProgressTracker**
   - Multi-step progress indicator
   - Real-time status updates
   - Error state handling

4. **KPICard**
   - Metric display with trend indicator
   - Drill-down capability
   - Export options

5. **FilterBar**
   - Global filter controls
   - Saved filter sets
   - Quick date ranges

6. **ChatButton**
   - Floating action button
   - Notification badge
   - Smooth open/close animation

7. **ChatWindow**
   - Resizable chat interface
   - Message history
   - Input field with send button
   - Minimize/maximize controls

8. **MessageBubble**
   - User/AI message differentiation
   - Timestamp display
   - Copy message functionality

9. **PeriodSelector**
   - Week-over-week option
   - Month-over-month option
   - Custom date range picker

### 6.4 Responsive Design
- Desktop-first design (1440px baseline)
- Tablet support (768px - 1024px)
- Mobile view (<768px):
  - Chat interface hidden
  - KPI cards stack vertically
  - Tables use horizontal scroll
  - Simplified navigation

---

## 7. Technical Architecture

### 7.1 Frontend Stack
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Shadcn/ui
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **Charts**: Recharts or D3.js

### 7.2 Routing Structure

```
/                     → Redirects to /dashboard
/dashboard            → Main analytics overview
/dashboard/products   → Product-specific analytics
/dashboard/topics     → Topic-specific analytics
/admin/setup          → Admin setup flow start
/admin/setup/source   → Step 1: Data source selection
/admin/setup/mapping  → Step 2: Field mapping
/admin/setup/preview  → Step 3: Preview & confirm
```

### 7.3 API Layer (Stubs)
*Note: No authentication required for MVP*

#### Data Source Endpoints
```typescript
GET    /api/snowflake/databases
GET    /api/snowflake/schemas/{database}
GET    /api/snowflake/tables/{database}/{schema}
GET    /api/snowflake/preview/{database}/{schema}/{table}
```

#### Configuration Endpoints
```typescript
POST   /api/config/mapping
GET    /api/config/mapping/{id}
PUT    /api/config/mapping/{id}
DELETE /api/config/mapping/{id}
POST   /api/config/generate-fields
GET    /api/config/generation-status/{jobId}
```

#### Analytics Endpoints
```typescript
GET    /api/analytics/overview?period=week|month&comparison=true
GET    /api/analytics/products?period=week|month&comparison=true
GET    /api/analytics/topics?period=week|month&comparison=true
GET    /api/analytics/trends
POST   /api/analytics/export
```

#### Chat Agent Endpoints
```typescript
POST   /api/chat/message
GET    /api/chat/history/{sessionId}
POST   /api/chat/feedback/{messageId}
GET    /api/chat/suggestions
```

### 7.4 Data Models

#### Configuration Model
```typescript
interface DataSourceConfig {
  id: string;
  name: string;
  database: string;
  schema: string;
  tables: string[];
  mappings: FieldMapping[];
  createdAt: Date;
  updatedAt: Date;
  status: 'draft' | 'active' | 'archived';
}

interface FieldMapping {
  targetField: 'timestamp' | 'topic' | 'product' | 'feature';
  sourceType: 'column' | 'generated';
  sourceColumn?: string;
  generationType?: 'llm' | 'regex' | 'lookup';
  generationConfig?: Record<string, any>;
}
```

#### Analytics Model
```typescript
interface KPIMetric {
  id: string;
  name: string;
  value: number;
  previousValue: number;
  change: number;
  changePercentage: number;
  changeType: 'increase' | 'decrease' | 'neutral';
  period: 'week' | 'month' | 'custom';
  comparisonPeriod: string;
  drillDownEnabled: boolean;
}

interface ProductMetrics {
  productId: string;
  productName: string;
  productCategory: string;
  parentProduct?: string;
  metrics: {
    totalCases: KPIMetric;
    avgCaseLife: KPIMetric;
    resolutionRate: KPIMetric;
  };
  topIssues: Issue[];
  trend: TrendData[];
}

interface PeriodComparison {
  currentPeriod: {
    start: Date;
    end: Date;
    label: string;
  };
  previousPeriod: {
    start: Date;
    end: Date;
    label: string;
  };
  comparisonType: 'week' | 'month' | 'custom';
}
```

#### Chat Model
```typescript
interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    queriedData?: string[];
    suggestedQueries?: string[];
  };
}

interface ChatSession {
  id: string;
  userId: string;
  startTime: Date;
  lastActivity: Date;
  messages: ChatMessage[];
  context: Record<string, any>;
}
```

---

## 8. API Stub Specifications

### 8.1 Backend Service Stubs

```typescript
// Snowflake Data Service (Stub)
class SnowflakeService {
  async getDatabases(): Promise<string[]> {
    // Stub: Return mock databases
    return ['SUPPORT_DB', 'CUSTOMER_DB', 'PRODUCT_DB'];
  }

  async getTables(database: string, schema: string): Promise<TableInfo[]> {
    // Stub: Return mock tables
    return [
      { name: 'support_tickets', rowCount: 50000 },
      { name: 'call_transcripts', rowCount: 25000 }
    ];
  }

  async previewTable(params: PreviewParams): Promise<any[]> {
    // Stub: Return sample data
    return generateMockTickets(10);
  }
}

// Taxonomy Generation Service (Stub)
class TaxonomyService {
  async generateFields(config: FieldMapping): Promise<GenerationJob> {
    // Stub: Return job ID and status
    return {
      jobId: 'job_' + Date.now(),
      status: 'processing',
      estimatedTime: 300
    };
  }

  async getJobStatus(jobId: string): Promise<JobStatus> {
    // Stub: Return mock progress
    return {
      jobId,
      status: 'completed',
      progress: 100,
      results: { processed: 1000, errors: 0 }
    };
  }
}

// Analytics Service (Stub)
class AnalyticsService {
  async getOverviewMetrics(period: string, comparison: boolean): Promise<KPIMetric[]> {
    // Stub: Return pre-calculated metrics with period comparisons
    return [
      {
        id: 'total_cases',
        name: 'Total Cases',
        value: 1250,
        previousValue: 1100,
        change: 150,
        changePercentage: 13.6,
        changeType: 'increase',
        period: period as 'week' | 'month',
        comparisonPeriod: 'Previous ' + period,
        drillDownEnabled: true
      }
      // ... more metrics
    ];
  }
}

// Chat Agent Service (Stub)
class ChatAgentService {
  async sendMessage(message: string, sessionId: string): Promise<ChatMessage> {
    // Stub: Return AI response
    return {
      id: 'msg_' + Date.now(),
      sessionId,
      role: 'assistant',
      content: 'Based on the data, I can see that...',
      timestamp: new Date(),
      metadata: {
        queriedData: ['support_tickets', 'product_metrics'],
        suggestedQueries: [
          'Show me trending issues',
          'Compare this month to last month'
        ]
      }
    };
  }

  async getHistory(sessionId: string): Promise<ChatMessage[]> {
    // Stub: Return chat history
    return [];
  }
}
```

---

## 9. Data Volume & Performance Considerations

### 9.1 Data Scale
- **Expected Volume**: 100,000 to millions of support tickets
- **Growth Rate**: Continuous accumulation of historical data
- **Query Performance**: Backend optimized for large-scale aggregations

### 9.2 Refresh Strategy
- **MVP**: Manual refresh or on-demand
- **Future**: Automated hourly/daily refresh
- **Caching**: Frontend caches API responses for performance
- **Loading States**: Progressive loading for large datasets

### 9.3 Backend Processing
- **Pre-calculated Metrics**: All KPIs computed by backend
- **Materialized Views**: For performance optimization
- **Incremental Processing**: Only new data processed in refreshes

### 9.4 Frontend Performance Guidelines
- **Data Fetching**: TanStack Query with 5-minute cache time
- **List Virtualization**: Use react-window for lists over 100 items
- **Search Debouncing**: 300ms delay on all search inputs
- **Lazy Loading**: Charts load with skeleton states
- **Parallel Loading**: Analytics data fetched concurrently
- **Memory Management**: Stale-while-revalidate pattern

---

## 10. MVP vs Future Features

### 10.1 MVP Features (Phase 1)
- **Fixed Metrics**:
  - Average cases (period comparison)
  - Average case life (period comparison)
  - Resolution rate (period comparison)
  - All metrics by product/feature
- **Fixed Taxonomy**: Predefined categories and hierarchies
- **Basic Chat**: Stubbed AI agent with mock responses
- **Manual Refresh**: Admin-triggered data updates
- **Dark Mode UI**: Default and only theme
- **No Authentication**: Direct access for MVP
- **Basic Error Handling**: Simple retry logic, elegant loading states
- **Limited Mobile Support**: View-only, chat hidden

### 10.2 Future Features (Post-MVP)
- **Custom Metrics**: User-defined KPIs and calculations
- **Custom Taxonomy**: Flexible category definitions
- **Advanced Chat**: Full AI agent integration with Snowflake Cortex
- **Automated Refresh**: Scheduled hourly/daily updates
- **Real-time Updates**: Live data streaming
- **Export Capabilities**: PDF, Excel, API access
- **Multi-tenant Support**: Organization-level isolation
- **Advanced Visualizations**: Custom charts and dashboards
- **Authentication**: SSO/OAuth integration
- **Full Mobile Support**: Responsive design for all features

### 10.3 Dummy Data Specifications (MVP)
- **Volume**: ~10,000 support tickets for performance testing
- **Product Hierarchy**:
  - Categories: Analytics, Infrastructure, Security
  - Products: Dashboard, Reports, API, Authentication, Database
  - Features: Export, Import, Visualization, Performance, etc.
- **Realistic Patterns**:
  - Seasonal trends
  - Product-specific issue clusters
  - Resolution rate variations
- **Edge Cases**: Empty states, loading states, error scenarios

---

## 11. Success Metrics

### 11.1 Adoption Metrics
- Number of active configurations
- Daily active users (DAU)
- Feature adoption rate

### 11.2 Performance Metrics
- Time to complete setup flow (<5 minutes)
- Dashboard load time (<2 seconds)
- Field generation processing time

### 11.3 Business Metrics
- Reduction in manual analysis time
- Increase in identified product issues
- Improvement in support response time

---

## 12. Implementation Phases

### Phase 1: MVP (Weeks 1-4)
- Basic admin setup flow
- Analytics dashboard with fixed metrics
- Dark mode UI implementation
- Chat interface with stubbed responses
- Core API stubs
- Dummy data generator for testing

### Phase 2: Enhanced Analytics (Weeks 5-8)
- Advanced filtering
- Drill-down capabilities
- Export functionality

### Phase 3: Optimization (Weeks 9-12)
- Performance improvements
- Additional visualizations
- Configuration templates

---

## 13. Open Questions

1. What authentication method should be used (SSO, OAuth, basic)?
2. Should there be role-based access control in v1?
3. What are the specific Snowflake compute requirements?
4. Should we support scheduling for automated updates?
5. What export formats are required (CSV, PDF, API)?

---

## 14. Appendix

### A. Mock Data Examples
```json
{
  "ticket": {
    "id": "TICK-001",
    "created_at": "2024-01-15T10:30:00Z",
    "body": "Unable to export reports in the new dashboard",
    "status": "closed",
    "resolution_time_hours": 24,
    "generated_topic": "Export Issues",
    "generated_product_category": "Analytics",
    "generated_product": "Dashboard",
    "generated_feature": "Report Export"
  },
  "kpi_metric": {
    "id": "avg_case_life",
    "name": "Average Case Life",
    "value": 18.5,
    "previousValue": 22.3,
    "change": -3.8,
    "changePercentage": -17.0,
    "changeType": "decrease",
    "period": "week",
    "comparisonPeriod": "Previous week",
    "unit": "hours"
  },
  "chat_message": {
    "user": "What's the resolution rate for Dashboard issues this month?",
    "assistant": "The resolution rate for Dashboard issues this month is 87.5%, which is up 5.2% from last month (82.3%). The top resolved issues were related to Export functionality (45%) and Performance (30%)."
  }
}
```

### B. Error States
- Connection failures
- Mapping validation errors
- Generation timeout
- Insufficient permissions

### C. Future Considerations
- Real-time data streaming
- Machine learning model management
- Multi-language support
- Advanced visualization options
