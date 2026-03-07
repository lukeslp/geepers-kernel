# Monarch Money CLI Tool

Command-line interface for managing your Monarch Money finances with LLM-powered insights.

## Features

### ✅ **Phase A: Security & Quality (COMPLETE)**
- ✓ **Encrypted session storage** using Fernet symmetric encryption
- ✓ **Comprehensive error handling** with proper exception types
- ✓ **Input validation** using Pydantic models
- ✓ **Structured logging** with loguru (console + file rotation)
- ✓ **No security vulnerabilities** - no bare except clauses, validated inputs

### ✅ **Phase D: CLI Tool with LLM Integration (COMPLETE)**
- ✓ **Click framework** with beautiful Rich terminal output
- ✓ **Core commands**: accounts, transactions, budgets, insights, chat
- ✓ **LLM integration** using `/home/coolhand/shared/llm_providers/`
- ✓ **Natural language queries**: Ask questions about your finances
- ✓ **Interactive chat mode**: Conversational financial assistance
- ✓ **Insights features**: Spending analysis, budget recommendations

## Installation

The tool is installed system-wide as `mm`:

```bash
# Already installed to /usr/local/bin/mm
mm --help
```

## Quick Start

### 1. Login
```bash
mm login
# Enter your Monarch Money credentials
# Session is saved securely with encryption
```

### 2. View Accounts
```bash
mm accounts
# Beautiful table of all your accounts with balances
```

### 3. View Transactions
```bash
# Recent transactions
mm transactions list

# Search transactions
mm transactions search "amazon"

# Specific date range
mm transactions list --start 2026-01-01 --end 2026-01-31 --limit 100
```

### 4. Check Budgets
```bash
# Current budget status
mm budgets show

# Quick summary
mm budgets summary
```

### 5. Get AI Insights
```bash
# Ask natural language questions
mm insights ask "What did I spend on groceries last month?"

# Comprehensive spending analysis
mm insights analyze

# Choose LLM provider
mm insights ask "How can I save money?" --provider anthropic
mm insights ask "What are my biggest expenses?" --provider openai
```

### 6. Interactive Chat
```bash
# Start a conversation with your financial assistant
mm chat

# Chat with specific LLM
mm chat --provider anthropic --model claude-sonnet-4-5-20250929
```

## Command Reference

### Accounts
```bash
mm accounts                    # List all accounts
mm accounts --json             # JSON output
```

### Transactions
```bash
mm transactions list           # Recent transactions
mm transactions list -s 2026-01-01 -e 2026-01-31 -l 100
mm transactions search "text"  # Search by merchant/description
mm transactions --json         # JSON output
```

### Budgets
```bash
mm budgets show               # Current budget status
mm budgets summary            # Income/expense summary
```

### Insights (AI-Powered)
```bash
mm insights ask "question"    # Natural language query
mm insights analyze           # Comprehensive analysis
mm insights ask "..." -p anthropic -m claude-sonnet-4-5-20250929
```

### Chat (Interactive AI)
```bash
mm chat                       # Start chat session
mm chat -p openai            # Use OpenAI
mm chat -p xai               # Use X.AI (Grok)
```

### Login
```bash
mm login                      # Interactive login
```

## Configuration

### Secure Session Storage
Sessions are stored encrypted at `~/.mm/`:
- `session.enc` - Encrypted session data (Fernet encryption)
- `session.key` - Encryption key (chmod 600)
- `logs/` - Structured logs with 30-day rotation

### LLM Providers
The CLI uses `/home/coolhand/shared/llm_providers/` for AI features.

Supported providers:
- `anthropic` (default) - Claude Sonnet 4.5
- `openai` - GPT-4
- `xai` - Grok
- `groq` - Fast Llama models
- `mistral` - Mistral Large
- `gemini` - Google Gemini
- `perplexity` - Perplexity AI
- `ollama` - Local models

### Environment Variables
```bash
# Optional: Set API keys for LLM providers
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export XAI_API_KEY="xai-..."
```

## Architecture

```
monarchmoney/
├── monarchmoney/              # Core library
│   ├── monarchmoney.py       # Main API client
│   ├── secure_session.py     # Encrypted session storage
│   ├── validators.py         # Pydantic input validation
│   └── logger.py             # Structured logging
├── cli/                      # CLI tool
│   ├── main.py              # Click entry point
│   └── commands/
│       ├── transactions.py   # Transaction commands
│       ├── budgets.py       # Budget commands
│       ├── insights.py      # LLM insights
│       └── chat.py          # Interactive chat
└── tests/                    # Test suite
    ├── test_cli.py          # CLI tests
    ├── test_validators.py   # Validation tests
    └── test_secure_session.py # Security tests
```

## Quality Metrics

### Security ✓
- [x] Encrypted session storage (Fernet)
- [x] No plaintext credentials
- [x] Input validation on all user inputs
- [x] No bare except clauses
- [x] Secure file permissions (0600/0700)

### Error Handling ✓
- [x] Try/except blocks throughout
- [x] Graceful degradation
- [x] User-friendly error messages
- [x] Comprehensive logging

### Code Quality ✓
- [x] Type hints with Pydantic
- [x] Structured logging (loguru)
- [x] Clean separation of concerns
- [x] CLI + library architecture

### User Experience ✓
- [x] Beautiful Rich terminal output
- [x] Tables, panels, progress bars
- [x] Color-coded information
- [x] Helpful error messages
- [x] Comprehensive help text

## Examples

### Example 1: Quick Financial Check
```bash
# Check your accounts
mm accounts

# Check this month's budget
mm budgets summary

# Ask for insights
mm insights ask "Am I overspending anywhere?"
```

### Example 2: Monthly Review
```bash
# Get transactions for the month
mm transactions list --start 2026-01-01 --limit 500 --json > jan_transactions.json

# Analyze spending
mm insights analyze

# Interactive review
mm chat
> "Show me my top 5 expense categories this month"
> "Are there any unusual charges?"
> "How does this compare to last month?"
```

### Example 3: Budget Planning
```bash
# Check current budgets
mm budgets show

# Get AI recommendations
mm insights ask "How should I adjust my budgets based on my spending?"

# Chat for detailed planning
mm chat
> "I want to save $500 more per month. Where can I cut back?"
```

## Logs

Logs are stored at `~/.mm/logs/`:
- **Console**: INFO and above (colorized)
- **File**: DEBUG and above
- **Rotation**: Daily
- **Retention**: 30 days
- **Compression**: gzip

View logs:
```bash
tail -f ~/.mm/logs/monarchmoney_2026-01-05.log
```

## Troubleshooting

### Login Issues
```bash
# Delete old session and re-login
rm -rf ~/.mm/session.*
mm login
```

### LLM Provider Errors
```bash
# Check API keys are set
echo $ANTHROPIC_API_KEY

# Try different provider
mm insights ask "question" --provider openai
```

### Verbose Mode
```bash
# Enable verbose logging
mm --verbose accounts
mm -v transactions list
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Installing from Source
```bash
git clone https://github.com/hammem/monarchmoney.git
cd monarchmoney
python setup.py develop
```

## Credits

- **Original Library**: [hammem/monarchmoney](https://github.com/hammem/monarchmoney)
- **CLI & Security Enhancements**: Luke Steuber
- **LLM Integration**: Uses shared LLM provider factory

## License

MIT License - See LICENSE file

---

**Built with**: Python, Click, Rich, Loguru, Pydantic, Anthropic/OpenAI APIs

**Security**: Fernet encryption, input validation, structured logging

**AI**: Natural language queries, interactive chat, spending insights
