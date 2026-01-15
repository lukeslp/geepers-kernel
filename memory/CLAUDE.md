# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: memory

Redis-based caching and state management utilities for LLM responses, rate limiting, and key-value storage.

### Overview

The memory module provides:
- **RedisManager** - Redis connection and operations
- Key-value storage with TTL support
- Semantic caching for LLM responses
- Rate limiting counters
- Session state management

### RedisManager

Manage Redis connections and operations:

```python
from memory import RedisManager

# Connect to Redis
redis = RedisManager(
    host='localhost',
    port=6379,
    db=0
)

# Or use environment variables
# REDIS_HOST, REDIS_PORT
redis = RedisManager()

# Basic operations
redis.set('key', 'value')
value = redis.get('key')

# With TTL (time-to-live in seconds)
redis.set('session:123', {'user': 'john'}, ttl=3600)  # Expire in 1 hour

# Check if key exists
if redis.exists('key'):
    print("Key exists")

# Delete key
redis.delete('key')

# Set TTL on existing key
redis.expire('key', 300)  # Expire in 5 minutes
```

### Caching LLM Responses

Cache expensive LLM calls:

```python
from memory import RedisManager
import hashlib
import json

redis = RedisManager()

def cache_llm_response(messages, response, ttl=3600):
    """Cache LLM response with messages as key"""
    # Create cache key from messages
    cache_key = hashlib.sha256(
        json.dumps(messages, sort_keys=True).encode()
    ).hexdigest()

    # Store response
    redis.set(f"llm:cache:{cache_key}", response, ttl=ttl)

def get_cached_response(messages):
    """Get cached LLM response"""
    cache_key = hashlib.sha256(
        json.dumps(messages, sort_keys=True).encode()
    ).hexdigest()

    return redis.get(f"llm:cache:{cache_key}")

# Usage
messages = [{'role': 'user', 'content': 'What is AI?'}]

# Check cache first
cached = get_cached_response(messages)
if cached:
    response = cached
else:
    # Make API call
    response = provider.complete(messages)
    # Cache result
    cache_llm_response(messages, response, ttl=3600)
```

### Counter Operations

Track counts and implement rate limiting:

```python
redis = RedisManager()

# Increment counter
count = redis.increment('api:calls:today')
print(f"API calls today: {count}")

# Increment by amount
redis.increment('tokens:used', amount=1500)

# Rate limiting
def check_rate_limit(user_id, limit=100, window=60):
    """Check if user is within rate limit"""
    key = f"rate_limit:{user_id}"

    # Increment and get current count
    current = redis.increment(key)

    # Set TTL on first request
    if current == 1:
        redis.expire(key, window)

    return current <= limit

# Usage
if check_rate_limit('user123', limit=100, window=60):
    # Process request
    pass
else:
    raise Exception("Rate limit exceeded")
```

### Session Management

Store session data:

```python
redis = RedisManager()

# Create session
def create_session(session_id, data, ttl=3600):
    redis.set(f"session:{session_id}", data, ttl=ttl)

# Get session
def get_session(session_id):
    return redis.get(f"session:{session_id}")

# Update session
def update_session(session_id, data):
    session = get_session(session_id)
    if session:
        session.update(data)
        redis.set(f"session:{session_id}", session, ttl=3600)

# Delete session
def delete_session(session_id):
    redis.delete(f"session:{session_id}")

# Usage
create_session('abc123', {
    'user_id': 'user123',
    'created_at': '2024-01-01T12:00:00'
})

session = get_session('abc123')
print(session['user_id'])
```

### Workflow State

Store orchestrator workflow state:

```python
redis = RedisManager()

def save_workflow_state(task_id, state):
    """Save workflow state"""
    redis.set(f"workflow:{task_id}", state, ttl=86400)  # 24 hours

def get_workflow_state(task_id):
    """Get workflow state"""
    return redis.get(f"workflow:{task_id}")

def update_workflow_progress(task_id, progress):
    """Update workflow progress"""
    state = get_workflow_state(task_id)
    if state:
        state['progress'] = progress
        save_workflow_state(task_id, state)

# Usage
save_workflow_state('task-123', {
    'status': 'running',
    'progress': 0,
    'started_at': '2024-01-01T12:00:00'
})

# Update progress
update_workflow_progress('task-123', 50)
```

### Key Patterns

Use consistent key naming:

```python
# Namespaces
redis.set('app:config:version', '1.0')
redis.set('app:user:123', {'name': 'John'})
redis.set('app:cache:response:abc', 'cached response')

# Time-based keys
from datetime import date
today = date.today().isoformat()
redis.set(f'metrics:{today}', {'calls': 100})

# Hierarchical keys
redis.set('provider:openai:config', {'api_key': '...'})
redis.set('provider:openai:usage:2024-01', {'tokens': 10000})
```

### Batch Operations

Work with multiple keys:

```python
redis = RedisManager()

# Store multiple values
data = {
    'user:1': {'name': 'Alice'},
    'user:2': {'name': 'Bob'},
    'user:3': {'name': 'Charlie'}
}

for key, value in data.items():
    redis.set(key, value)

# Pattern matching (use with caution)
import re
# Get all user keys
# Note: Use SCAN in production, not KEYS
all_keys = redis.client.keys('user:*')
users = {key: redis.get(key) for key in all_keys}
```

### TTL Management

Manage expiration times:

```python
redis = RedisManager()

# Set with TTL
redis.set('temp:data', 'value', ttl=300)  # 5 minutes

# Update TTL on existing key
redis.expire('temp:data', 600)  # Extend to 10 minutes

# Get remaining TTL
ttl = redis.client.ttl('temp:data')
print(f"{ttl} seconds remaining")

# Remove TTL (make persistent)
redis.client.persist('temp:data')
```

### Integration with Providers

Cache provider responses:

```python
from memory import RedisManager
from llm_providers import ProviderFactory
import hashlib
import json

redis = RedisManager()
provider = ProviderFactory.get_provider('xai')

def cached_complete(messages, ttl=3600):
    """Complete with caching"""
    # Create cache key
    cache_key = hashlib.sha256(
        json.dumps(messages, sort_keys=True).encode()
    ).hexdigest()

    # Check cache
    cached = redis.get(f"llm:{cache_key}")
    if cached:
        return cached

    # Make API call
    response = provider.complete(messages)

    # Cache response
    redis.set(f"llm:{cache_key}", {
        'content': response.content,
        'model': response.model,
        'usage': response.usage
    }, ttl=ttl)

    return response

# Usage
response = cached_complete([
    {'role': 'user', 'content': 'What is AI?'}
])
```

### Error Handling

Handle Redis errors gracefully:

```python
from memory import RedisManager

try:
    redis = RedisManager(host='localhost', port=6379)
except ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    # Fall back to in-memory cache or no cache
    redis = None

def safe_get(key, default=None):
    """Get from Redis with fallback"""
    if redis:
        try:
            return redis.get(key)
        except Exception as e:
            print(f"Redis error: {e}")
    return default

def safe_set(key, value, ttl=None):
    """Set in Redis with error handling"""
    if redis:
        try:
            return redis.set(key, value, ttl)
        except Exception as e:
            print(f"Redis error: {e}")
    return False
```

### Testing

```python
import pytest
from memory import RedisManager

@pytest.fixture
def redis():
    """Redis instance for testing"""
    r = RedisManager(db=15)  # Use separate DB for tests
    yield r
    # Cleanup
    r.client.flushdb()

def test_set_and_get(redis):
    redis.set('test_key', 'test_value')
    assert redis.get('test_key') == 'test_value'

def test_ttl(redis):
    redis.set('temp', 'value', ttl=1)
    assert redis.exists('temp')
    import time
    time.sleep(2)
    assert not redis.exists('temp')

def test_counter(redis):
    count1 = redis.increment('counter')
    count2 = redis.increment('counter')
    assert count1 == 1
    assert count2 == 2
```

### Files in This Module

- `__init__.py` - RedisManager class and utilities

### Dependencies

Required:
- `redis` - Python Redis client (`pip install redis`)

Optional:
- Redis server running locally or remotely

### Configuration

Via environment variables:

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
```

Or programmatically:

```python
redis = RedisManager(
    host='redis.example.com',
    port=6379,
    db=0
)
```

### Best Practices

- Always set TTL for cached data to prevent memory bloat
- Use namespaced keys (e.g., `app:feature:key`)
- Handle connection errors gracefully
- Use separate Redis databases for different environments (dev, test, prod)
- Monitor Redis memory usage
- Use SCAN instead of KEYS for production pattern matching
- Serialize complex objects to JSON before storing
- Clean up expired keys regularly
- Use connection pooling for high-traffic applications
- Set reasonable TTLs based on data freshness requirements

### Common Patterns

#### Distributed Lock
```python
def acquire_lock(redis, lock_key, ttl=10):
    """Acquire distributed lock"""
    # SET NX EX pattern
    return redis.client.set(lock_key, '1', nx=True, ex=ttl)

def release_lock(redis, lock_key):
    """Release lock"""
    redis.delete(lock_key)

# Usage
if acquire_lock(redis, 'lock:process', ttl=30):
    try:
        # Critical section
        process_data()
    finally:
        release_lock(redis, 'lock:process')
```

#### Leaderboard
```python
def update_score(redis, user_id, score):
    """Update user score in sorted set"""
    redis.client.zadd('leaderboard', {user_id: score})

def get_top_users(redis, limit=10):
    """Get top users"""
    return redis.client.zrevrange('leaderboard', 0, limit-1, withscores=True)
```

#### Pub/Sub
```python
# Publisher
def publish_event(redis, channel, message):
    redis.client.publish(channel, json.dumps(message))

# Subscriber
def subscribe_events(redis, channel):
    pubsub = redis.client.pubsub()
    pubsub.subscribe(channel)
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            handle_event(data)
```

### Performance Tips

- Use pipelining for multiple operations
- Batch operations when possible
- Set appropriate TTLs to avoid memory issues
- Use Redis Cluster for high availability
- Monitor slow queries
- Use connection pooling
- Compress large values before storing

### Security

- Use authentication (requirepass)
- Restrict network access
- Use TLS for connections over network
- Don't store sensitive data without encryption
- Regularly update Redis version
- Monitor for unusual access patterns
