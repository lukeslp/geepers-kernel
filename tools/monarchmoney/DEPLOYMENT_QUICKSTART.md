# Monarch Money CLI - Deployment Quick Start

**Last Updated**: 2026-01-05
**Status**: Ready for Phase 1 Implementation

---

## TL;DR

Transform this library into a production CLI tool accessible as `mm` command.

**Timeline**: 8 days
**Cost**: ~$27/month (LLM API)
**Infrastructure**: No service manager needed (CLI only)
**Port**: None (add 5055 later for web UI)

---

## Quick Commands

### Initial Setup
```bash
cd /home/coolhand/tools/monarchmoney
git add -A && git commit -m "checkpoint before CLI deployment"
git checkout -b feature/cli-deployment
```

### Install CLI
```bash
# Add to setup.py
entry_points={
    'console_scripts': ['mm=cli.main:cli'],
}

# Install
pip install -e .

# Verify
mm --version
```

### Create Config
```bash
mkdir -p ~/.config/monarchmoney/logs
mkdir -p ~/.cache/monarchmoney

# Set environment
export MONARCH_EMAIL="your@email.com"
export ANTHROPIC_API_KEY="sk-ant-..."

# Initialize
mm config init
mm login
```

### Test
```bash
mm accounts list
mm transactions list --limit 5
mm ask "What's my balance?"
mm insights spending
mm chat
```

---

## Deployment Phases

### Phase 1: Security Fixes (1-2 days)
**Launch**: `@geepers_orchestrator_python` + `@geepers_security`

**Tasks**:
- Fix bare except clauses
- Add input validation
- Encrypt session storage
- Add logging framework
- Secure credential management

**Verification**:
```bash
pytest tests/  # All tests pass
mm login       # Works with encryption
```

---

### Phase 2: CLI Structure (1-2 days)
**Launch**: `@geepers_pycli`

**Tasks**:
- Install Click framework
- Create command groups
- Add Rich formatting
- Implement core commands

**Verification**:
```bash
mm --help              # Shows all commands
mm accounts list       # Returns data
mm transactions search "test"  # Works
```

---

### Phase 3: LLM Integration (2-3 days)
**Launch**: `@geepers_integrator`

**Tasks**:
- Link to /home/coolhand/shared/llm_providers/
- Create prompt templates
- Build query engine
- Add interactive chat

**Verification**:
```bash
mm ask "What did I spend on groceries?"  # LLM responds
mm insights budget                       # Analysis works
mm chat                                  # Interactive mode
```

---

### Phase 4: Testing (1 day)
**Launch**: `@geepers_testing` + `@geepers_validator`

**Tasks**:
- Integration tests
- Security audit
- Performance testing
- Documentation

**Verification**:
```bash
pytest tests/ --cov=cli    # >80% coverage
mm --help                  # Documentation complete
```

---

### Phase 5: Deployment (1 day)
**Launch**: `@geepers_orchestrator_deploy`

**Tasks**:
- System-wide install
- Log rotation setup
- Documentation
- Deployment report

**Verification**:
```bash
which mm                   # /usr/local/bin/mm
mm --version              # Shows version
ls ~/.config/monarchmoney # Config exists
```

---

## Architecture Decisions

### 1. Installation: System Package (pip install -e .)
**Why**: Standard, easy updates, no service needed

### 2. No Service Manager for MVP
**Why**: CLI runs on-demand, no background daemon needed
**Future**: Add service for web dashboard

### 3. No Port Allocation for MVP
**Why**: CLI doesn't need network port
**Future**: Port 5055 reserved for web UI

### 4. Use Existing LLM Infrastructure
**Why**: Leverage /home/coolhand/shared/llm_providers/
**How**: Import factory, use complexity router

### 5. Security-First
**Why**: Financial data is sensitive
**How**: Encrypted sessions, OS keyring, audit logs

---

## File Locations

### Code
- **Source**: `/home/coolhand/tools/monarchmoney/`
- **CLI**: `/home/coolhand/tools/monarchmoney/cli/`
- **LLM**: `/home/coolhand/tools/monarchmoney/cli/llm/`

### Configuration
- **Config**: `~/.config/monarchmoney/config.yaml`
- **Logs**: `~/.config/monarchmoney/logs/`
- **Cache**: `~/.cache/monarchmoney/`

### Security
- **Sessions**: `~/.config/monarchmoney/session.enc` (encrypted)
- **Keys**: OS keyring (via keyring library)
- **Audit**: `~/.config/monarchmoney/logs/audit.log`

---

## LLM Integration

### Provider Setup
```python
import sys
sys.path.append('/home/coolhand/shared/llm_providers')

from factory import LLMProviderFactory
from complexity_router import ComplexityRouter

factory = LLMProviderFactory()
client = factory.create('anthropic')
```

### Example Query
```python
response = await client.chat_completion(
    messages=[{
        "role": "user",
        "content": "Analyze my budget: {budget_data}"
    }],
    model="claude-sonnet-4.5",
    temperature=0.3
)
```

---

## Security Checklist

- [ ] Sessions encrypted (Fernet)
- [ ] API keys in environment variables
- [ ] OS keyring for sensitive data
- [ ] File permissions correct (600 for configs)
- [ ] Audit logging enabled
- [ ] Input validation on all commands
- [ ] No secrets in git

---

## Cost Breakdown

### Infrastructure
- **Server**: $0 (using dr.eamer.dev)
- **Storage**: ~100MB (negligible)
- **Bandwidth**: Minimal

### LLM API (Anthropic Claude)
- **Input**: $3 per 1M tokens
- **Output**: $15 per 1M tokens
- **Estimated**: ~$27/month (moderate usage)

### Total: ~$27/month

---

## Rollback Plan

### If Something Breaks
```bash
# 1. Stop services (if any)
sm stop mm-dashboard

# 2. Restore code
cd /home/coolhand/tools/monarchmoney
git checkout main

# 3. Restore config
cp -r ~/.config/monarchmoney.backup.YYYYMMDD ~/.config/monarchmoney

# 4. Uninstall
pip uninstall monarchmoney

# 5. Document
echo "Rollback: <reason>" >> ~/geepers/logs/deploy-$(date +%Y-%m-%d).log
```

---

## Success Criteria

### Functional
- [x] `mm` command accessible system-wide
- [ ] Core commands working (accounts, transactions, budgets)
- [ ] LLM queries functional
- [ ] Interactive chat mode
- [ ] Configuration system

### Security
- [ ] Encrypted sessions
- [ ] Secure API key storage
- [ ] Audit logging
- [ ] Input validation

### Performance
- [ ] CLI commands < 2s response
- [ ] LLM queries < 10s response
- [ ] Cache reducing API calls

---

## Next Steps

1. **Review Full Plan**:
   `/home/coolhand/geepers/reports/by-date/2026-01-05/deploy-monarchmoney-cli.md`

2. **Launch Agents** (in order):
   - `@geepers_orchestrator_python` - Security fixes
   - `@geepers_pycli` - CLI structure
   - `@geepers_integrator` - LLM integration
   - `@geepers_orchestrator_deploy` - Final deployment

3. **Start Development**:
   ```bash
   cd /home/coolhand/tools/monarchmoney
   git checkout -b feature/cli-deployment
   # Begin Phase 1
   ```

---

## Questions?

- **Full Deployment Plan**: `/home/coolhand/geepers/reports/by-date/2026-01-05/deploy-monarchmoney-cli.md`
- **Project Assessment**: `/home/coolhand/geepers/recommendations/by-project/monarchmoney.md`
- **Quick Start**: `/home/coolhand/geepers/recommendations/by-project/monarchmoney-quick-start.md`

---

**Ready to Deploy**: Yes
**Estimated Time**: 8 days
**Risk Level**: Low
**Next Action**: Launch security fixes with @geepers_orchestrator_python
