#!/usr/bin/env python3
"""
Cost Tracking Dashboard

Display AI API costs for the current day and recent activity.

Usage:
    python3 view_costs.py               # Today's costs
    python3 view_costs.py --date 2025-11-20  # Specific date
    python3 view_costs.py --week        # Last 7 days
    python3 view_costs.py --month       # Last 30 days

Author: Luke Steuber
"""

import sys
import os
from datetime import date, timedelta, datetime
from decimal import Decimal

# Add shared library to path
sys.path.insert(0, '/home/coolhand/shared')

try:
    from observability import get_cost_tracker, get_metrics_collector
except ImportError:
    print("Error: Could not import observability modules")
    print("Make sure you're in the correct directory and shared library is installed")
    sys.exit(1)


def format_currency(amount: Decimal) -> str:
    """Format decimal as currency."""
    return f"${amount:.4f}"


def print_daily_costs(target_date: date):
    """Print costs for a specific day."""
    tracker = get_cost_tracker()
    daily = tracker.get_daily_costs(target_date)
    
    print(f"\n{'='*80}")
    print(f"  AI API Costs for {target_date.strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")
    
    if daily.total_cost == 0:
        print("  No costs recorded for this date.\n")
        return
    
    print(f"  Total Cost: {format_currency(daily.total_cost)}")
    print(f"  Total Calls: {daily.call_count:,}")
    print(f"  Tokens Used: {daily.total_tokens:,}")
    print()
    
    if daily.by_provider:
        print("  Costs by Provider:")
        print("  " + "-" * 76)
        print(f"  {'Provider':<20} {'Calls':>10} {'Tokens':>15} {'Cost':>15}")
        print("  " + "-" * 76)
        
        # Sort by cost descending
        sorted_providers = sorted(
            daily.by_provider.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for provider, cost in sorted_providers:
            # Get provider stats
            provider_calls = 0  # Would need to track separately
            provider_tokens = 0
            print(f"  {provider:<20} {provider_calls:>10} {provider_tokens:>15,} {format_currency(cost):>15}")
        
        print("  " + "-" * 76)
    
    if daily.by_model:
        print("\n  Costs by Model:")
        print("  " + "-" * 76)
        print(f"  {'Model':<30} {'Calls':>10} {'Cost':>15}")
        print("  " + "-" * 76)
        
        # Sort by cost descending
        sorted_models = sorted(
            daily.by_model.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for model, cost in sorted_models[:10]:  # Top 10
            print(f"  {model:<30} {'-':>10} {format_currency(cost):>15}")
        
        if len(daily.by_model) > 10:
            print(f"  ... and {len(daily.by_model) - 10} more models")
        
        print("  " + "-" * 76)
    
    print()


def print_week_costs():
    """Print costs for the last 7 days."""
    tracker = get_cost_tracker()
    
    print(f"\n{'='*80}")
    print(f"  AI API Costs - Last 7 Days")
    print(f"{'='*80}\n")
    
    today = date.today()
    total_week_cost = Decimal('0')
    
    print(f"  {'Date':<15} {'Calls':>10} {'Tokens':>15} {'Cost':>15}")
    print("  " + "-" * 76)
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        daily = tracker.get_daily_costs(target_date)
        
        date_str = target_date.strftime('%Y-%m-%d')
        if i == 0:
            date_str += " (today)"
        
        print(f"  {date_str:<15} {daily.call_count:>10,} {daily.total_tokens:>15,} {format_currency(daily.total_cost):>15}")
        total_week_cost += daily.total_cost
    
    print("  " + "-" * 76)
    print(f"  {'TOTAL':<15} {'-':>10} {'-':>15} {format_currency(total_week_cost):>15}")
    print()


def print_month_costs():
    """Print costs for the last 30 days."""
    tracker = get_cost_tracker()
    
    print(f"\n{'='*80}")
    print(f"  AI API Costs - Last 30 Days")
    print(f"{'='*80}\n")
    
    today = date.today()
    total_month_cost = Decimal('0')
    weekly_totals = []
    
    # Group by week
    for week in range(4):
        week_start = today - timedelta(days=6 + (week * 7))
        week_end = today - timedelta(days=week * 7)
        week_cost = Decimal('0')
        
        for i in range(7):
            target_date = week_end - timedelta(days=i)
            if target_date < week_start:
                continue
            daily = tracker.get_daily_costs(target_date)
            week_cost += daily.total_cost
        
        weekly_totals.append((week_start, week_end, week_cost))
        total_month_cost += week_cost
    
    print(f"  {'Week':<30} {'Cost':>15}")
    print("  " + "-" * 76)
    
    for i, (start, end, cost) in enumerate(reversed(weekly_totals)):
        week_label = f"{start.strftime('%b %d')} - {end.strftime('%b %d')}"
        if i == 0:
            week_label += " (this week)"
        print(f"  {week_label:<30} {format_currency(cost):>15}")
    
    print("  " + "-" * 76)
    print(f"  {'TOTAL (30 days)':<30} {format_currency(total_month_cost):>15}")
    print()


def print_summary_stats():
    """Print overall summary statistics."""
    metrics = get_metrics_collector()
    stats = metrics.get_stats()
    
    print(f"\n{'='*80}")
    print(f"  Overall Statistics")
    print(f"{'='*80}\n")
    
    if 'providers' in stats:
        provider_stats = stats['providers']
        print(f"  Total API Calls: {provider_stats.get('total_calls', 0):,}")
        print(f"  Total Cost: {format_currency(Decimal(str(provider_stats.get('total_cost_usd', 0))))}")
        print(f"  Average Cost per Call: {format_currency(Decimal(str(provider_stats.get('avg_cost_per_call', 0))))}")
    
    if 'tools' in stats:
        tool_stats = stats['tools']
        print(f"\n  Tool Calls: {tool_stats.get('total_calls', 0):,}")
        if 'by_name' in tool_stats:
            print("\n  Most Used Tools:")
            sorted_tools = sorted(
                tool_stats['by_name'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for tool, count in sorted_tools:
                print(f"    - {tool}: {count:,} calls")
    
    print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='View AI API cost tracking dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Show today's costs
  %(prog)s --date 2025-11-20    Show costs for specific date
  %(prog)s --week               Show last 7 days
  %(prog)s --month              Show last 30 days
  %(prog)s --summary            Show overall statistics
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Specific date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--week',
        action='store_true',
        help='Show last 7 days'
    )
    parser.add_argument(
        '--month',
        action='store_true',
        help='Show last 30 days'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show overall statistics'
    )
    
    args = parser.parse_args()
    
    try:
        if args.week:
            print_week_costs()
        elif args.month:
            print_month_costs()
        elif args.summary:
            print_summary_stats()
        elif args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            print_daily_costs(target_date)
        else:
            # Default: today's costs
            print_daily_costs(date.today())
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

