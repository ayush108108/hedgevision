# Page Tests

This directory contains tests for page-level components.

## Running Tests

```bash
# From frontend-v2 directory

# Run all tests
npm test

# Run only page tests
npm test pages/

# Run specific test file
npm test PairAnalysisPage.test.tsx

# Run with watch mode
npm test -- --watch

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

## Test Coverage

### PairAnalysisPage.test.tsx ✅

**Covered Scenarios:**
- ✅ Loading state (displays "Analyzing pair relationship...")
- ✅ Error state (displays error message)
- ✅ Success state (displays analysis data)
- ✅ Loading → Success transition
- ✅ Loading → Error transition
- ✅ Initial render with default values
- ✅ Configuration controls present
- ✅ Refresh button functionality

**Test Count:** 15 tests

**What's Tested:**
1. Loading indicator appears when fetching data
2. Error messages display correctly with proper styling
3. Successful data renders without loading/error states
4. State transitions work smoothly
5. UI elements render correctly
6. Default asset selections (Apple, Microsoft)
7. Button states (enabled/disabled based on loading)

## Adding New Tests

### Template for New Page Test

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { YourPage } from './YourPage';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('YourPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render', () => {
    renderWithProviders(<YourPage />);
    expect(screen.getByText('Page Title')).toBeInTheDocument();
  });
});
```

## Test Patterns

### 1. Test Loading State
```typescript
it('shows loading state', async () => {
  vi.mocked(api.fetch).mockImplementation(() => new Promise(() => {}));
  renderWithProviders(<Page />);
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
});
```

### 2. Test Error State
```typescript
it('shows error state', async () => {
  vi.mocked(api.fetch).mockRejectedValue(new Error('Failed'));
  renderWithProviders(<Page />);
  await waitFor(() => {
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });
});
```

### 3. Test Success State
```typescript
it('shows data', async () => {
  vi.mocked(api.fetch).mockResolvedValue({ data: 'test' });
  renderWithProviders(<Page />);
  await waitFor(() => {
    expect(screen.getByText('test')).toBeInTheDocument();
  });
});
```

## Quick Reference

### Install Dependencies
```bash
npm install
```

### Run Tests Once
```bash
npm test -- --run
```

### Watch Mode (Development)
```bash
npm test
```

### Coverage Report
```bash
npm run test:coverage
```

### Debug Specific Test
```bash
npm test -- -t "test name"
```

## See Also

- [TESTING.md](../../TESTING.md) - Comprehensive testing guide
- [Vitest Docs](https://vitest.dev/) - Test framework documentation
- [React Testing Library](https://testing-library.com/react) - Testing utilities

