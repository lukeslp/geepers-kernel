#!/usr/bin/env python3
"""
API Authentication CLI

Command-line tool for managing API keys

Usage:
    python cli.py generate --prefix bliss --email user@example.com --tier basic
    python cli.py list
    python cli.py list --email user@example.com
    python cli.py revoke <key_id>
    python cli.py usage --api blissAPI --days 7
    python cli.py stats

Author: Luke Steuber
"""

import argparse
import sys
import os
from tabulate import tabulate
from auth_manager import AuthManager


def cmd_generate(args):
    """Generate a new API key"""
    auth = AuthManager(args.db)

    key_info = auth.generate_api_key(
        prefix=args.prefix,
        user_email=args.email,
        tier=args.tier,
        api_name=args.api,
        expires_days=args.expires,
        notes=args.notes
    )

    print("=" * 80)
    print("API KEY GENERATED")
    print("=" * 80)
    print(f"\n⚠️  IMPORTANT: Save this key securely. It cannot be retrieved later!\n")
    print(f"API Key:    {key_info['api_key']}")
    print(f"Key ID:     {key_info['key_id']}")
    print(f"Prefix:     {key_info['key_prefix']}")
    print(f"Email:      {key_info['user_email']}")
    print(f"Tier:       {key_info['tier']}")
    print(f"API:        {key_info['api_name'] or 'All APIs'}")
    if key_info['expires_at']:
        print(f"Expires:    {key_info['expires_at']}")
    print("\n" + "=" * 80)


def cmd_list(args):
    """List API keys"""
    auth = AuthManager(args.db)

    keys = auth.list_keys(user_email=args.email, active_only=not args.all)

    if not keys:
        print("No API keys found.")
        return

    # Format for tabulate
    headers = ['Key ID', 'Prefix', 'Email', 'Tier', 'API', 'Created', 'Last Used', 'Status']
    rows = []

    for key in keys:
        status = 'Active' if key.get('is_active', 1) else 'Revoked'
        if key.get('expires_at'):
            status = f"Expires {key['expires_at'][:10]}"

        rows.append([
            key['key_id'][:8] + '...',
            key['key_prefix'],
            key['user_email'],
            key['tier'],
            key.get('api_name') or 'All',
            key['created_at'][:10] if key.get('created_at') else '',
            key['last_used_at'][:10] if key.get('last_used_at') else 'Never',
            status
        ])

    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nTotal: {len(keys)} keys")


def cmd_revoke(args):
    """Revoke an API key"""
    auth = AuthManager(args.db)

    success = auth.revoke_key(args.key_id)

    if success:
        print(f"✓ API key {args.key_id} has been revoked.")
    else:
        print(f"✗ API key {args.key_id} not found.")
        sys.exit(1)


def cmd_usage(args):
    """Show usage statistics"""
    auth = AuthManager(args.db)

    stats = auth.get_usage_stats(api_name=args.api, days=args.days)

    if not stats:
        print("No usage data found.")
        return

    headers = ['API', 'Endpoint', 'Requests', 'Cache Hits', 'Avg Response (ms)', 'Users', 'Days']
    rows = []

    for stat in stats:
        cache_pct = 0
        if stat['total_requests'] > 0:
            cache_pct = (stat['cache_hits'] / stat['total_requests']) * 100

        rows.append([
            stat['api_name'],
            stat['endpoint'],
            stat['total_requests'],
            f"{stat['cache_hits']} ({cache_pct:.1f}%)",
            stat['avg_response_ms'] or 'N/A',
            stat['unique_users'],
            stat['active_days']
        ])

    print(f"\nUsage Statistics (Last {args.days} days)")
    print(tabulate(rows, headers=headers, tablefmt='grid'))


def cmd_stats(args):
    """Show overall statistics"""
    auth = AuthManager(args.db)

    with auth._get_connection() as conn:
        # Total keys
        cursor = conn.execute("SELECT COUNT(*) as count FROM api_keys WHERE is_active = 1")
        active_keys = cursor.fetchone()['count']

        # Total requests
        cursor = conn.execute("SELECT COUNT(*) as count FROM api_usage")
        total_requests = cursor.fetchone()['count']

        # Requests by API
        cursor = conn.execute("""
            SELECT api_name, COUNT(*) as count
            FROM api_usage
            GROUP BY api_name
            ORDER BY count DESC
        """)
        api_counts = cursor.fetchall()

        # Keys by tier
        cursor = conn.execute("""
            SELECT tier, COUNT(*) as count
            FROM api_keys
            WHERE is_active = 1
            GROUP BY tier
        """)
        tier_counts = cursor.fetchall()

    print("\n=== API Authentication Statistics ===\n")
    print(f"Active API Keys:     {active_keys}")
    print(f"Total API Requests:  {total_requests:,}")

    if tier_counts:
        print("\nKeys by Tier:")
        for row in tier_counts:
            print(f"  {row['tier']:10} {row['count']:5}")

    if api_counts:
        print("\nRequests by API:")
        for row in api_counts:
            print(f"  {row['api_name']:20} {row['count']:,}")


def main():
    parser = argparse.ArgumentParser(description="API Authentication Management CLI")
    parser.add_argument('--db', default="/home/coolhand/data/api_auth.db",
                        help="Path to authentication database")

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a new API key')
    gen_parser.add_argument('--prefix', required=True, help='Key prefix (e.g., bliss, lang)')
    gen_parser.add_argument('--email', required=True, help='User email address')
    gen_parser.add_argument('--tier', default='basic', choices=['free', 'basic', 'premium'],
                            help='Rate limit tier (default: basic)')
    gen_parser.add_argument('--api', help='Restrict key to specific API name')
    gen_parser.add_argument('--expires', type=int, help='Expiration in days')
    gen_parser.add_argument('--notes', help='Optional notes about the key')

    # List command
    list_parser = subparsers.add_parser('list', help='List API keys')
    list_parser.add_argument('--email', help='Filter by user email')
    list_parser.add_argument('--all', action='store_true', help='Include inactive/expired keys')

    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke an API key')
    revoke_parser.add_argument('key_id', help='Key ID to revoke')

    # Usage command
    usage_parser = subparsers.add_parser('usage', help='Show usage statistics')
    usage_parser.add_argument('--api', help='Filter by API name')
    usage_parser.add_argument('--days', type=int, default=7, help='Number of days (default: 7)')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show overall statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'revoke':
        cmd_revoke(args)
    elif args.command == 'usage':
        cmd_usage(args)
    elif args.command == 'stats':
        cmd_stats(args)


if __name__ == "__main__":
    main()
