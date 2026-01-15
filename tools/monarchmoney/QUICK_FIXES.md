# Monarch Money CLI - Quick Fixes Reference

**Most Critical Issues First** - Copy/paste ready

---

## 🔴 CRITICAL FIX #1: Enable Encrypted Sessions (5 minutes)

**File**: `monarchmoney/monarchmoney.py` line 124

**Current (BROKEN)**:
```python
if use_saved_session and os.path.exists(self._session_file):
    print(f"Using saved session found at {self._session_file}")
    self.load_session(self._session_file)
    return
```

**Replace with**:
```python
# Check for encrypted session first
if use_saved_session and self._use_secure_storage and self._session_manager:
    if self._session_manager.session_exists():
        try:
            session_data = self._session_manager.load_session()
            self._token = session_data.get("token")
            logger.info("Using encrypted saved session")
            return
        except Exception as e:
            logger.warning(f"Failed to load encrypted session: {e}")
            # Fall through to login

# Fallback to old pickle (for migration)
if use_saved_session and os.path.exists(self._session_file):
    logger.info(f"Migrating old session from {self._session_file}")
    self.load_session(self._session_file)
    # Re-save as encrypted
    if self._use_secure_storage and self._session_manager:
        self._session_manager.save_session({"token": self._token})
        logger.info("Session migrated to encrypted storage")
    return
```

---

## 🔴 CRITICAL FIX #2: Fix Bare Exception Handlers (5 minutes)

**File**: `cli/commands/insights.py` lines 55-58, 60-64

**Current (BROKEN)**:
```python
try:
    budgets = await mm.get_budgets()
except:  # ❌ Catches Ctrl+C!
    budgets = {}
```

**Replace ALL instances with**:
```python
try:
    budgets = await mm.get_budgets()
except Exception as e:  # ✅ Only catches errors
    logger.warning(f"Failed to load budgets: {e}")
    budgets = {}
```

**Files to fix**:
- `cli/commands/insights.py`: lines 55-58, 60-64, 122-125, 127-130
- `cli/commands/chat.py`: lines 38-41, 43-46

---

## 🔴 CRITICAL FIX #3: Remove Print Statements (2 minutes)

**File**: `monarchmoney/monarchmoney.py` line 125

**Current**:
```python
print(f"Using saved session found at {self._session_file}")
```

**Replace with**:
```python
logger.info("Using saved session")
```

---

## 🟡 IMPORTANT FIX #4: Date Filtering (10 minutes)

**File**: `cli/commands/transactions.py` line 54

**Current (BROKEN - dates validated but not used)**:
```python
await mm.login(use_saved_session=True)
transactions = await mm.get_transactions(limit=limit)
```

**Replace with**:
```python
await mm.login(use_saved_session=True)

# Apply date filters if provided
filter_params = {'limit': limit}
if start:
    filter_params['start_date'] = start_date.isoformat()
if end:
    filter_params['end_date'] = end_date.isoformat()

transactions = await mm.get_transactions(**filter_params)
```

**Note**: Check if `get_transactions()` supports date params. If not, filter in Python:
```python
transactions = await mm.get_transactions(limit=limit)

# Filter by date
results = transactions.get('allTransactions', {}).get('results', [])
filtered = [
    txn for txn in results
    if start_date <= datetime.fromisoformat(txn['date']).date() <= end_date
]
```

---

## 🟢 QUICK WIN #1: Add Balance Command (15 minutes)

**File**: `cli/main.py` (add before `if __name__ == '__main__':`)

```python
@cli.command()
def balance():
    """Quick balance check across all accounts."""
    async def get_balance():
        from monarchmoney.monarchmoney import MonarchMoney
        mm = MonarchMoney(use_secure_storage=True)

        try:
            await mm.login(use_saved_session=True)
            accounts_data = await mm.get_accounts()

            total = sum(
                acc.get('currentBalance', 0)
                for acc in accounts_data.get('accounts', [])
                if not acc.get('isHidden', False)
            )

            console.print(f"\n[bold green]Total Balance:[/bold green] [cyan]${total:,.2f}[/cyan]\n")
            logger.info(f"Balance check: ${total:.2f}")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logger.error(f"Balance check failed: {str(e)}")
            raise click.Abort()

    asyncio.run(get_balance())
```

**Test**: `mm balance` should show total quickly

---

## 🟢 QUICK WIN #2: Add Config File (30 minutes)

**File**: `cli/config.py` (create new file)

```python
"""Configuration management for Monarch Money CLI."""
import yaml
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path.home() / ".mm" / "config.yaml"

DEFAULT_CONFIG = {
    "defaults": {
        "llm_provider": "anthropic",
        "transaction_limit": 100,
        "date_range_days": 30,
    },
    "display": {
        "show_icons": True,
        "table_style": "rounded",
    },
    "cache": {
        "enabled": True,
        "ttl_seconds": 300,
    }
}

def load_config() -> Dict[str, Any]:
    """Load config from file or return defaults."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)

def save_config(config: Dict[str, Any]) -> None:
    """Save config to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False)

def get_default(key: str, default: Any = None) -> Any:
    """Get a default value from config."""
    config = load_config()
    keys = key.split('.')
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    return value if value is not None else default
```

**File**: Update `requirements.txt`
```
pyyaml>=6.0
```

**File**: Update `cli/main.py` to use config
```python
from cli.config import get_default

# In commands, use:
provider = get_default('defaults.llm_provider', 'anthropic')
limit = get_default('defaults.transaction_limit', 100)
```

---

## 🟢 QUICK WIN #3: Add Caching (1 hour)

**File**: `cli/cache.py` (create new file)

```python
"""Simple file-based caching for API responses."""
import json
import time
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path.home() / ".mm" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cached(key: str, ttl_seconds: int = 300) -> Optional[Any]:
    """Get cached data if still valid."""
    cache_file = CACHE_DIR / f"{key}.json"

    if not cache_file.exists():
        return None

    with open(cache_file) as f:
        cached = json.load(f)

    # Check expiry
    if time.time() - cached['timestamp'] > ttl_seconds:
        cache_file.unlink()  # Delete expired cache
        return None

    return cached['data']

def set_cached(key: str, data: Any) -> None:
    """Save data to cache."""
    cache_file = CACHE_DIR / f"{key}.json"

    with open(cache_file, 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'data': data
        }, f, default=str)

def clear_cache() -> None:
    """Clear all cached data."""
    for cache_file in CACHE_DIR.glob("*.json"):
        cache_file.unlink()
```

**Usage in commands**:
```python
from cli.cache import get_cached, set_cached

async def get_accounts():
    # Try cache first
    cached = get_cached('accounts', ttl_seconds=300)
    if cached:
        return cached

    # Fetch from API
    mm = MonarchMoney(use_secure_storage=True)
    await mm.login(use_saved_session=True)
    accounts = await mm.get_accounts()

    # Cache for 5 minutes
    set_cached('accounts', accounts)
    return accounts
```

**Add clear cache command**:
```python
@cli.command()
def clear_cache():
    """Clear all cached data."""
    from cli.cache import clear_cache as do_clear
    do_clear()
    console.print("[green]Cache cleared[/green]")
```

---

## Testing Checklist

After applying fixes:

```bash
# 1. Test encrypted session
mm login
ls -la ~/.mm/  # Should see session.enc and session.key

# 2. Test session reuse
mm accounts  # Should not re-prompt for login
mm balance   # Should load from encrypted session

# 3. Test Ctrl+C works
mm chat  # Try Ctrl+C during data loading - should exit cleanly

# 4. Test date filtering
mm transactions list --start 2025-12-01 --end 2025-12-31

# 5. Test caching
time mm accounts  # First run (slow)
time mm accounts  # Second run (fast!)

# 6. Test config
cat ~/.mm/config.yaml
mm config  # Should show current settings
```

---

## Deployment

```bash
cd /home/coolhand/tools/monarchmoney

# Commit fixes
git add -A
git commit -m "fix: critical session management and error handling bugs

- Enable encrypted session storage
- Fix bare exception handlers
- Implement date filtering
- Add caching layer
- Add balance command
- Add config file support"

# Reinstall
sudo pip install -e . --force-reinstall

# Verify
mm --version
mm balance
```

---

## File Summary

**Files to modify**:
1. `monarchmoney/monarchmoney.py` - session management fix
2. `cli/commands/insights.py` - exception handlers
3. `cli/commands/chat.py` - exception handlers
4. `cli/commands/transactions.py` - date filtering
5. `cli/main.py` - add balance command

**Files to create**:
1. `cli/config.py` - configuration management
2. `cli/cache.py` - caching layer

**Files to update**:
1. `requirements.txt` - add pyyaml

**Total time**: ~2 hours for all critical + quick win fixes
