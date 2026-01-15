# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library that provides programmatic access to Monarch Money's API. The library uses GraphQL for all data operations and implements async/await patterns throughout.

**Key Architecture:**
- Single-file module design: `monarchmoney/monarchmoney.py` (~3000 lines)
- GraphQL client using `gql` library with `aiohttp` transport
- Session-based authentication with pickle serialization for session persistence
- All API methods are async and must be called with `await` or `asyncio.run()`

## Development Commands

### Installation & Setup
```bash
# Install locally for development
make install

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run unit tests
python -m unittest tests/test_monarchmoney.py

# CI runs both Black (linting) and unit tests
```

### Code Formatting
```bash
# Format code with Black (REQUIRED before commits)
black .

# CI will reject PRs that don't pass Black formatting
```

### Building & Distribution
```bash
# Build distribution packages
make builddist

# Upload to PyPI (maintainers only)
make twine

# Clean build artifacts
make clean
```

### Example Usage
```bash
# Run the example script
python main.py
```

## Authentication Architecture

The library supports three authentication patterns:

1. **Interactive login** (iPython/Jupyter): `await mm.interactive_login()`
   - Prompts for email, password, and MFA if needed

2. **Non-interactive with exception handling**:
   ```python
   try:
       await mm.login(email, password)
   except RequireMFAException:
       await mm.multi_factor_authenticate(email, password, mfa_code)
   ```

3. **MFA Secret Key** (recommended for automation):
   ```python
   await mm.login(email=email, password=password, mfa_secret_key=key)
   ```

**Session Management:**
- Sessions are pickled to `.mm/mm_session.pickle` by default
- Session includes both cookies and auth token
- Sessions can last several months
- Use `save_session()` and `load_session()` to persist across runs

## GraphQL Query Pattern

All data-fetching methods follow the same pattern:

1. Define a GraphQL query using `gql()` wrapper
2. Call `self.gql_call(operation="OperationName", graphql_query=query)`
3. The `gql_call` method handles:
   - Creating GraphQL client with auth headers
   - Making the async request
   - Error handling and token refresh

**Example:**
```python
async def get_accounts(self) -> Dict[str, Any]:
    query = gql("""
        query GetAccounts {
            accounts {
                ...AccountFields
            }
        }
        fragment AccountFields on Account {
            id
            displayName
            currentBalance
        }
    """)
    return await self.gql_call(operation="GetAccounts", graphql_query=query)
```

## Key Classes & Endpoints

**MonarchMoneyEndpoints:**
- `BASE_URL`: https://api.monarchmoney.com
- `getLoginEndpoint()`: `/auth/login/`
- `getGraphQL()`: `/graphql`
- `getAccountBalanceHistoryUploadEndpoint()`: `/account-balance-history/upload/`

**Custom Exceptions:**
- `RequireMFAException`: Raised when MFA is required
- `LoginFailedException`: Authentication failed
- `RequestFailedException`: GraphQL request failed

## Testing Strategy

Tests use `unittest.IsolatedAsyncioTestCase` for async test support.

**Mock Pattern:**
```python
@patch.object(Client, "execute_async")
async def test_get_accounts(self, mock_execute_async):
    mock_execute_async.return_value = TestMonarchMoney.loadTestData(
        filename="get_accounts.json"
    )
    result = await self.monarch_money.get_accounts()
```

Test data is stored in `tests/*.json` files with sample API responses.

## Important Implementation Notes

- **All methods are async**: Must use `await` or `asyncio.run()`
- **Session file location**: Configurable via constructor, defaults to `.mm/mm_session.pickle`
- **Timeout**: Configurable via `set_timeout()`, defaults to 10 seconds
- **Token-based auth**: Can bypass login by providing token directly in constructor
- **Date formats**: Methods expect ISO format strings (e.g., "2023-10-01")
- **GraphQL fragments**: Reusable field sets defined inline with queries

## API Method Categories

**Read-only (Non-mutating):**
- Accounts: `get_accounts()`, `get_account_holdings()`, `get_account_history()`
- Transactions: `get_transactions()`, `get_transaction_details()`, `get_transaction_splits()`
- Budgets: `get_budgets()`
- Cashflow: `get_cashflow()`, `get_cashflow_summary()`
- Metadata: `get_transaction_categories()`, `get_transaction_tags()`, `get_institutions()`

**Mutating operations:**
- Transactions: `create_transaction()`, `update_transaction()`, `delete_transaction()`
- Categories: `create_transaction_category()`, `delete_transaction_category()`
- Accounts: `create_manual_account()`, `update_account()`, `delete_account()`
- Budgets: `set_budget_amount()`
- Refresh: `request_accounts_refresh()`, `request_accounts_refresh_and_wait()`

## Common Pitfalls

1. **Forgetting await**: All API methods are async
2. **Session expiration**: Check for authentication errors and re-login
3. **MFA handling**: Interactive flows work best; automation needs MFA secret key
4. **Date ranges**: Transaction queries default to last 100; use `start_date`/`end_date` for ranges
5. **Black formatting**: CI will fail if code isn't formatted with Black
