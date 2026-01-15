# MonarchMoney Enhancement Roadmap
**Created**: 2026-01-05
**Full Assessment**: /home/coolhand/geepers/reports/by-date/2026-01-05/python-monarchmoney.md

## Quick Start Guide

This roadmap outlines the transformation of monarchmoney from a library into a full-featured CLI tool with LLM integration for finance beginners.

## Current State
- ✅ Async GraphQL library (2,923 lines in single file)
- ✅ Session-based authentication with MFA support
- ✅ 58 methods for accounts, transactions, budgets, cashflow
- ⚠️ No CLI interface
- ⚠️ Inconsistent error handling
- ⚠️ No LLM integration
- ⚠️ Needs refactoring

## Target State
- 🎯 Multi-file modular library
- 🎯 Beautiful CLI with Click + Rich
- 🎯 LLM-powered financial assistant
- 🎯 Beginner-friendly workflows
- 🎯 Comprehensive error handling
- 🎯 80%+ test coverage

## Phase 1: Core Refactoring (Week 1)

### Goals
- Split monolithic file into logical modules
- Implement proper error handling
- Add logging and validation

### Tasks
1. **Create Module Structure**
   ```bash
   monarchmoney/
   ├── client.py           # Main class
   ├── auth.py            # Authentication
   ├── exceptions.py      # Error hierarchy
   ├── models/            # Data models
   │   ├── account.py
   │   ├── transaction.py
   │   └── budget.py
   ├── queries/           # GraphQL queries
   │   ├── accounts.py
   │   ├── transactions.py
   │   └── budgets.py
   └── utils/
       ├── validation.py
       └── retry.py
   ```

2. **Exception Hierarchy**
   ```python
   MonarchMoneyError
   ├── AuthenticationError
   │   ├── LoginFailedException
   │   └── RequireMFAException
   ├── ValidationError
   ├── APIError
   │   └── RequestFailedException
   └── NetworkError
   ```

3. **Add Logging**
   - Replace all `print()` with `logger` calls
   - Configure structured logging
   - Add debug mode

4. **Add Validation**
   - Input validation for all public methods
   - Date validation helpers
   - Enum validation for timeframes

### Deliverables
- [ ] Modular codebase
- [ ] Exception hierarchy implemented
- [ ] Logging throughout
- [ ] Input validation on all public methods
- [ ] Tests still passing

### Estimated Time: 16-20 hours

---

## Phase 2: CLI Tool (Week 2-3)

### Goals
- Build intuitive CLI with Click
- Beautiful output with Rich
- User-friendly for finance beginners

### Tasks
1. **CLI Framework Setup**
   ```bash
   monarchmoney/cli/
   ├── main.py              # Entry point
   ├── commands/
   │   ├── auth.py          # login, logout
   │   ├── accounts.py      # account commands
   │   ├── transactions.py  # transaction commands
   │   ├── budgets.py       # budget commands
   │   └── reports.py       # financial reports
   ├── formatters/
   │   ├── table.py         # Rich tables
   │   ├── json.py          # JSON output
   │   └── charts.py        # ASCII charts
   └── config.py            # CLI configuration
   ```

2. **Core Commands**
   ```bash
   # Authentication
   mm login
   mm logout
   mm status

   # Accounts
   mm accounts list
   mm accounts show <id>
   mm accounts balance [--summary]

   # Transactions
   mm transactions list [--limit N]
   mm transactions search <query>
   mm transactions export --format csv

   # Budgets
   mm budgets list
   mm budgets set <category> <amount>
   mm budgets report [--month YYYY-MM]

   # Reports
   mm reports cashflow [--start DATE] [--end DATE]
   mm reports net-worth [--trend]
   mm reports spending [--by-category]
   ```

3. **Output Formatters**
   - Rich tables for list views
   - Color-coded budget status (green/yellow/red)
   - Progress bars for budget usage
   - ASCII charts for trends
   - JSON export option

4. **User Experience**
   - Interactive login flow
   - Guided setup wizard
   - Helpful error messages
   - Example command suggestions

### Deliverables
- [ ] Working CLI with all core commands
- [ ] Beautiful Rich output
- [ ] Multiple output formats (table, JSON, CSV)
- [ ] Interactive mode for setup
- [ ] Help documentation
- [ ] CLI tests

### Estimated Time: 20-24 hours

---

## Phase 3: LLM Integration (Week 4-5)

### Goals
- Natural language interface to financial data
- Conversational financial assistant
- Integration with server's LLM infrastructure

### Tasks
1. **LLM Module Structure**
   ```bash
   monarchmoney/llm/
   ├── agent.py           # Main LLM agent
   ├── tools.py           # Tool definitions
   ├── prompts.py         # System prompts
   ├── context.py         # Conversation context
   └── providers/
       ├── anthropic.py   # Claude
       ├── openai.py      # GPT
       └── xai.py         # Grok
   ```

2. **Define LLM Tools**
   - `get_account_balance` - Check balances
   - `search_transactions` - Find transactions
   - `get_spending_summary` - Analyze spending
   - `get_budget_status` - Budget vs actual
   - `get_cashflow` - Income vs expenses
   - `analyze_trends` - Spending trends
   - `compare_periods` - Month over month

3. **Build Agent**
   - Use shared library providers: `/home/coolhand/shared/llm_providers/`
   - Implement tool execution
   - Context retention across conversation
   - Error handling for LLM failures

4. **CLI Integration**
   ```bash
   # Interactive chat
   mm chat

   # One-off questions
   mm ask "What did I spend on groceries last month?"
   mm ask "Show my net worth trend"
   mm ask "Am I over budget this month?"

   # Explanations
   mm explain budgets
   mm explain "Why is my spending high?"
   ```

5. **System Prompts**
   - Financial assistant persona
   - Guidelines for responses
   - Privacy and security awareness
   - Educational focus for beginners

### Deliverables
- [ ] LLM agent with tool execution
- [ ] Chat command in CLI
- [ ] Ask command for one-off queries
- [ ] Context retention
- [ ] Integration with 3+ providers
- [ ] System prompts optimized
- [ ] LLM tool tests

### Estimated Time: 16-20 hours

---

## Phase 4: Testing & Documentation (Week 6)

### Goals
- 80%+ test coverage
- Comprehensive documentation
- Example workflows for beginners

### Tasks
1. **Testing**
   ```bash
   tests/
   ├── unit/
   │   ├── test_client.py
   │   ├── test_auth.py
   │   ├── test_models.py
   │   └── test_validation.py
   ├── integration/
   │   ├── test_cli.py
   │   └── test_llm.py
   └── fixtures/
       ├── mock_responses.py
       └── sample_data.py
   ```

2. **Documentation**
   - CLI usage guide
   - LLM integration guide
   - API reference
   - Beginner tutorials
   - Example workflows

3. **User Guides**
   - Getting started
   - Understanding your finances
   - Budgeting with monarchmoney
   - Using the LLM assistant
   - Troubleshooting

### Deliverables
- [ ] 80%+ test coverage
- [ ] All tests passing
- [ ] CLI guide
- [ ] LLM guide
- [ ] Beginner tutorials
- [ ] Example workflows
- [ ] Updated README

### Estimated Time: 12-16 hours

---

## Implementation Priority

### Must Have (MVP)
1. Core refactoring
2. Exception handling
3. Basic CLI (auth, accounts, transactions)
4. Table output formatting
5. Simple LLM integration (ask command)

### Should Have
1. All CLI commands
2. Multiple output formats
3. Interactive chat mode
4. Rich output with colors/charts
5. Budget management commands

### Nice to Have
1. Advanced LLM features (trends, insights)
2. Financial education content
3. Goal tracking
4. Automated reports
5. Integration with other tools

---

## Technical Decisions

### CLI Framework: Click
**Why**: Industry standard, excellent for nested commands, great docs
**Alternative**: Typer (more modern, but less mature)

### Output Formatting: Rich
**Why**: Beautiful terminal output, progress bars, syntax highlighting
**Alternative**: Tabulate (simpler, but less features)

### LLM Provider: Multi-provider support
**Why**: Flexibility, leverage existing server infrastructure
**Providers**: Anthropic (Claude), OpenAI (GPT), XAI (Grok)

### Data Validation: Pydantic
**Why**: Type safety, automatic validation, great with Python 3.8+
**Alternative**: Marshmallow (more flexible, but more verbose)

### Testing: Pytest + pytest-asyncio
**Why**: Standard for async Python testing
**Coverage**: pytest-cov

### Logging: structlog
**Why**: Structured logging, easy to parse, great for debugging
**Alternative**: Standard logging (simpler, but less powerful)

---

## File Structure (Target)

```
monarchmoney/
├── monarchmoney/
│   ├── __init__.py
│   ├── client.py              # Main MonarchMoney class
│   ├── auth.py                # Authentication logic
│   ├── exceptions.py          # Exception hierarchy
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── account.py
│   │   ├── transaction.py
│   │   ├── budget.py
│   │   └── cashflow.py
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── accounts.py
│   │   ├── transactions.py
│   │   ├── budgets.py
│   │   └── cashflow.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validation.py
│   │   ├── retry.py
│   │   └── formatters.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── accounts.py
│   │   │   ├── transactions.py
│   │   │   ├── budgets.py
│   │   │   └── reports.py
│   │   ├── formatters/
│   │   │   ├── __init__.py
│   │   │   ├── table.py
│   │   │   ├── json.py
│   │   │   └── charts.py
│   │   └── config.py
│   └── llm/
│       ├── __init__.py
│       ├── agent.py
│       ├── tools.py
│       ├── prompts.py
│       ├── context.py
│       └── providers/
│           ├── __init__.py
│           ├── anthropic.py
│           ├── openai.py
│           └── xai.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── CLI_GUIDE.md
│   ├── LLM_INTEGRATION.md
│   ├── API_REFERENCE.md
│   └── BEGINNER_TUTORIAL.md
├── examples/
│   ├── basic_usage.py
│   ├── llm_chat.py
│   └── beginner_workflows.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── CHANGELOG.md
```

---

## Dependencies

### Core
```
aiohttp>=3.9.0,<4.0
gql[aiohttp]>=3.4.0,<4.0
oathtool>=2.3.0,<3.0
graphql-core>=3.2.0,<4.0
python-dotenv>=1.0.0,<2.0
pydantic>=2.0.0,<3.0
```

### CLI
```
click>=8.1.0,<9.0
rich>=13.0.0,<14.0
tabulate>=0.9.0,<1.0
```

### LLM
```
anthropic>=0.18.0,<1.0
openai>=1.12.0,<2.0
tenacity>=8.0.0,<9.0
```

### Development
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.7.0
```

---

## Example Usage (Target State)

### CLI Usage
```bash
# First time setup
$ mm login
Email: user@example.com
Password: ********
2FA Code: 123456
✓ Logged in successfully!

# Check accounts
$ mm accounts list
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Account            ┃ Type         ┃ Balance   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Checking           │ Depository   │ $2,345.67 │
│ Savings            │ Depository   │ $10,234.89│
│ Credit Card        │ Credit       │ -$1,234.56│
└────────────────────┴──────────────┴───────────┘

# Search transactions
$ mm transactions search "grocery" --limit 5
Found 5 transactions:
  2024-01-15  Whole Foods         -$87.42   Food & Dining
  2024-01-12  Trader Joe's        -$65.30   Food & Dining
  2024-01-08  Safeway             -$123.18  Food & Dining
  ...

# Check budget
$ mm budgets report
January 2024 Budget Status
┏━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Category     ┃ Budget ┃ Actual ┃ Left   ┃ Status   ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ Groceries    │ $400   │ $287   │ $113   │ ████░░░░ │
│ Dining Out   │ $200   │ $234   │ -$34   │ ████████ │
│ Gas          │ $150   │ $98    │ $52    │ ███░░░░░ │
└──────────────┴────────┴────────┴────────┴──────────┘
```

### LLM Usage
```bash
# Interactive chat
$ mm chat
Welcome to Monarch Money Assistant!

You: What did I spend on groceries last month?
Assistant: In December, you spent $342.18 on groceries across 23 transactions.
This is $57.82 under your $400 budget (14% savings). Great job!

You: Which stores did I shop at most?
Assistant: Your top grocery stores were:
1. Whole Foods - $142.30 (8 trips)
2. Trader Joe's - $98.75 (6 trips)
3. Safeway - $87.13 (5 trips)
4. Local Farmers Market - $14.00 (4 trips)

You: Am I spending more than last month?
Assistant: Compared to November ($378.42), you actually spent $36.24 less
in December. Your average transaction size decreased from $16.43 to $14.88.

# One-off questions
$ mm ask "What's my net worth?"
Your net worth is $11,345.00 as of today.
This is up $234.56 (2.1%) from last month.

$ mm ask "Show my biggest expense this month"
Your biggest expense this month was Rent Payment to ABC Properties
on January 1st for $1,200.00 (Housing category).
```

---

## Success Metrics

### Technical
- [ ] All 58+ methods preserved and working
- [ ] 80%+ test coverage
- [ ] Zero breaking changes to existing API
- [ ] CLI works on Linux, macOS, Windows
- [ ] Response time <2s for most commands

### User Experience
- [ ] Finance beginner can use without Python knowledge
- [ ] LLM answers 90%+ of natural language questions correctly
- [ ] Error messages are clear and actionable
- [ ] Setup takes <5 minutes
- [ ] CLI feels intuitive (validated by user testing)

### Code Quality
- [ ] No files >500 lines
- [ ] All public functions have docstrings
- [ ] Type hints on all functions
- [ ] Linting passes (Black, Ruff)
- [ ] No security vulnerabilities

---

## Risk Mitigation

### Breaking Changes
- **Risk**: Refactoring breaks existing code
- **Mitigation**: Keep old API intact, comprehensive tests, deprecation warnings

### LLM Reliability
- **Risk**: LLM gives wrong financial advice
- **Mitigation**: Clear disclaimers, validate all data, log all tool calls

### API Rate Limits
- **Risk**: Too many API calls
- **Mitigation**: Add caching, rate limiting, batch operations

### User Confusion
- **Risk**: CLI too complex for beginners
- **Mitigation**: User testing, guided setup, helpful defaults, examples

---

## Next Steps

1. Create feature branch: `git checkout -b feature/cli-llm-enhancement`
2. Start with Phase 1 (refactoring)
3. Commit frequently with clear messages
4. Test after each module split
5. Document as you go
6. User test early and often

## Questions to Resolve

1. Should we keep pickle session or move to keyring?
2. Which LLM provider should be default?
3. Should CLI support config files or just env vars?
4. What's the minimum Python version? (Recommend 3.8+)
5. Should we support offline mode with cached data?

---

**For detailed technical analysis, see**:
`/home/coolhand/geepers/reports/by-date/2026-01-05/python-monarchmoney.md`
