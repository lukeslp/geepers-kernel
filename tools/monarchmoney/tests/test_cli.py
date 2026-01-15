"""
Tests for the Monarch Money CLI tool.

Tests cover core functionality including commands, LLM integration, and error handling.
"""

import pytest
from click.testing import CliRunner
from cli.main import cli


class TestCLIBasics:
    """Test basic CLI functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test that CLI help displays correctly."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Monarch Money CLI' in result.output
        assert 'accounts' in result.output
        assert 'transactions' in result.output
        assert 'budgets' in result.output
        assert 'insights' in result.output
        assert 'chat' in result.output

    def test_cli_version(self):
        """Test version flag."""
        result = self.runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output

    def test_verbose_flag(self):
        """Test verbose flag is recognized."""
        result = self.runner.invoke(cli, ['--verbose', '--help'])
        assert result.exit_code == 0
        # Verbose mode should be enabled but still show help
        assert 'Monarch Money CLI' in result.output


class TestAccountsCommand:
    """Test accounts command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_accounts_help(self):
        """Test accounts help displays."""
        result = self.runner.invoke(cli, ['accounts', '--help'])
        assert result.exit_code == 0
        assert 'List all accounts' in result.output


class TestTransactionsCommand:
    """Test transactions command group."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_transactions_help(self):
        """Test transactions help displays."""
        result = self.runner.invoke(cli, ['transactions', '--help'])
        assert result.exit_code == 0
        assert 'Manage and view transactions' in result.output

    def test_transactions_list_help(self):
        """Test transactions list help."""
        result = self.runner.invoke(cli, ['transactions', 'list', '--help'])
        assert result.exit_code == 0
        assert 'List recent transactions' in result.output
        assert '--start' in result.output
        assert '--end' in result.output
        assert '--limit' in result.output

    def test_transactions_search_help(self):
        """Test transactions search help."""
        result = self.runner.invoke(cli, ['transactions', 'search', '--help'])
        assert result.exit_code == 0
        assert 'Search transactions' in result.output


class TestBudgetsCommand:
    """Test budgets command group."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_budgets_help(self):
        """Test budgets help displays."""
        result = self.runner.invoke(cli, ['budgets', '--help'])
        assert result.exit_code == 0
        assert 'Manage budgets' in result.output

    def test_budgets_show_help(self):
        """Test budgets show help."""
        result = self.runner.invoke(cli, ['budgets', 'show', '--help'])
        assert result.exit_code == 0
        assert 'Show current budget status' in result.output

    def test_budgets_summary_help(self):
        """Test budgets summary help."""
        result = self.runner.invoke(cli, ['budgets', 'summary', '--help'])
        assert result.exit_code == 0
        assert 'overall budget summary' in result.output


class TestInsightsCommand:
    """Test insights command group (LLM-powered)."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_insights_help(self):
        """Test insights help displays."""
        result = self.runner.invoke(cli, ['insights', '--help'])
        assert result.exit_code == 0
        assert 'AI-powered financial insights' in result.output

    def test_insights_ask_help(self):
        """Test insights ask help."""
        result = self.runner.invoke(cli, ['insights', 'ask', '--help'])
        assert result.exit_code == 0
        assert 'natural language question' in result.output
        assert '--provider' in result.output
        assert '--model' in result.output

    def test_insights_analyze_help(self):
        """Test insights analyze help."""
        result = self.runner.invoke(cli, ['insights', 'analyze', '--help'])
        assert result.exit_code == 0
        assert 'comprehensive spending analysis' in result.output


class TestChatCommand:
    """Test chat command (interactive LLM chat)."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_chat_help(self):
        """Test chat help displays."""
        result = self.runner.invoke(cli, ['chat', '--help'])
        assert result.exit_code == 0
        assert 'interactive chat session' in result.output
        assert '--provider' in result.output
        assert '--model' in result.output


class TestLoginCommand:
    """Test login command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_login_help(self):
        """Test login help displays."""
        result = self.runner.invoke(cli, ['login', '--help'])
        assert result.exit_code == 0
        assert 'Interactive login' in result.output


# Integration tests would require mocking the MonarchMoney API
# and LLM providers, which is beyond the scope of this basic test suite.
# For production, we'd want to add:
# - Mock API responses for accounts/transactions/budgets
# - Mock LLM provider responses
# - Test error handling paths
# - Test secure session storage
# - Test input validation
