"""
Unit tests for options screener
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from screener import (
    calculate_otm_percent,
    is_in_expiration_range,
    screen_options,
    EXPIRATION_RANGES
)


class TestCalculateOtmPercent:
    """Tests for the OTM percentage calculation"""

    def test_call_otm_positive(self):
        """Call with strike above current price should return positive OTM %"""
        # Strike $110, price $100 → 10% OTM
        result = calculate_otm_percent(strike=110, current_price=100, contract_type="call")
        assert result == 10.0

    def test_call_itm_negative(self):
        """Call with strike below current price should return negative OTM % (ITM)"""
        # Strike $90, price $100 → -10% (in the money)
        result = calculate_otm_percent(strike=90, current_price=100, contract_type="call")
        assert result == -10.0

    def test_call_atm(self):
        """Call with strike equal to current price should return 0%"""
        result = calculate_otm_percent(strike=100, current_price=100, contract_type="call")
        assert result == 0.0

    def test_put_otm_positive(self):
        """Put with strike below current price should return positive OTM %"""
        # Strike $90, price $100 → 10% OTM
        result = calculate_otm_percent(strike=90, current_price=100, contract_type="put")
        assert result == 10.0

    def test_put_itm_negative(self):
        """Put with strike above current price should return negative OTM % (ITM)"""
        # Strike $110, price $100 → -10% (in the money)
        result = calculate_otm_percent(strike=110, current_price=100, contract_type="put")
        assert result == -10.0

    def test_put_atm(self):
        """Put with strike equal to current price should return 0%"""
        result = calculate_otm_percent(strike=100, current_price=100, contract_type="put")
        assert result == 0.0

    def test_zero_current_price(self):
        """Should return 0 when current price is 0 to avoid division by zero"""
        result = calculate_otm_percent(strike=100, current_price=0, contract_type="call")
        assert result == 0

    def test_fractional_percentages(self):
        """Should handle fractional percentages correctly"""
        # Strike $105, price $100 → 5% OTM for calls
        result = calculate_otm_percent(strike=105, current_price=100, contract_type="call")
        assert result == 5.0

        # Strike $97.50, price $100 → 2.5% OTM for puts
        result = calculate_otm_percent(strike=97.5, current_price=100, contract_type="put")
        assert result == 2.5


class TestIsInExpirationRange:
    """Tests for the expiration range checking"""

    def test_within_1_3_month_range(self):
        """Expiration 45 days out should match 1-3m range"""
        future_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["1-3m"])
        assert result is True

    def test_within_lt1m_range(self):
        """Expiration 15 days out should match lt1m range"""
        future_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["lt1m"])
        assert result is True

    def test_outside_selected_range(self):
        """Expiration 200 days out should not match 1-3m range"""
        future_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["1-3m"])
        assert result is False

    def test_multi_select_matches_second_range(self):
        """Should return True if date matches any of the selected ranges"""
        # 45 days matches 1-3m but not lt1m
        future_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["lt1m", "1-3m"])
        assert result is True

    def test_multi_select_no_match(self):
        """Should return False if date matches none of the selected ranges"""
        # 200 days doesn't match lt1m or 1-3m
        future_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["lt1m", "1-3m"])
        assert result is False

    def test_all_ranges_selected(self):
        """Should match when all ranges are selected"""
        future_date = (datetime.now() + timedelta(days=300)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["lt1m", "1-3m", "3-5m", "5-8m", "8-12m"])
        assert result is True

    def test_invalid_date_format(self):
        """Should return False for invalid date strings"""
        result = is_in_expiration_range("invalid-date", ["1-3m"])
        assert result is False

    def test_none_date(self):
        """Should return False for None date"""
        result = is_in_expiration_range(None, ["1-3m"])
        assert result is False

    def test_empty_ranges(self):
        """Should return False when no ranges are selected"""
        future_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, [])
        assert result is False

    def test_invalid_range_key(self):
        """Should return False for invalid range keys"""
        future_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        result = is_in_expiration_range(future_date, ["invalid_range"])
        assert result is False

    def test_boundary_conditions(self):
        """Test boundary days for ranges"""
        # Test day 30 (last day of lt1m)
        date_30 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        assert is_in_expiration_range(date_30, ["lt1m"]) is True

        # Test day 32 (safely in 1-3m range, avoiding boundary precision issues)
        date_32 = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")
        assert is_in_expiration_range(date_32, ["1-3m"]) is True
        assert is_in_expiration_range(date_32, ["lt1m"]) is False


class TestScreenOptions:
    """Tests for the main screening function with mocked API calls"""

    @patch('screener.get_options_chain')
    @patch('screener.get_underlying_price')
    def test_filters_by_price(self, mock_underlying, mock_chain):
        """Should filter out options above max_price"""
        mock_chain.return_value = {
            "results": [
                {
                    "details": {
                        "ticker": "O:AAPL250221C00100000",
                        "strike_price": 100,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.03}  # Below max
                },
                {
                    "details": {
                        "ticker": "O:AAPL250221C00110000",
                        "strike_price": 110,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.10}  # Above max
                }
            ],
            "underlying_price": 100
        }

        result = screen_options(
            tickers=["AAPL"],
            max_price=0.05,
            contract_type="call",
            expiration_ranges=["1-3m"],
            otm_min=-100,
            otm_max=100
        )

        assert result["total_found"] == 1
        assert result["results"][0]["last_price"] == 0.03

    @patch('screener.get_options_chain')
    def test_filters_by_otm_range(self, mock_chain):
        """Should filter options outside OTM range"""
        mock_chain.return_value = {
            "results": [
                {
                    "details": {
                        "ticker": "O:AAPL250221C00105000",
                        "strike_price": 105,  # 5% OTM
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.02}
                },
                {
                    "details": {
                        "ticker": "O:AAPL250221C00120000",
                        "strike_price": 120,  # 20% OTM - should be filtered
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.01}
                }
            ],
            "underlying_price": 100
        }

        result = screen_options(
            tickers=["AAPL"],
            max_price=0.10,
            contract_type="call",
            expiration_ranges=["1-3m"],
            otm_min=0,
            otm_max=10  # Only 0-10% OTM
        )

        assert result["total_found"] == 1
        assert result["results"][0]["otm_percent"] == 5.0

    @patch('screener.get_options_chain')
    def test_filters_by_expiration(self, mock_chain):
        """Should filter options outside selected expiration ranges"""
        mock_chain.return_value = {
            "results": [
                {
                    "details": {
                        "ticker": "O:AAPL250221C00105000",
                        "strike_price": 105,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),  # 1-3m
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.02}
                },
                {
                    "details": {
                        "ticker": "O:AAPL250621C00105000",
                        "strike_price": 105,
                        "expiration_date": (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d"),  # 5-8m
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.02}
                }
            ],
            "underlying_price": 100
        }

        result = screen_options(
            tickers=["AAPL"],
            max_price=0.10,
            contract_type="call",
            expiration_ranges=["1-3m"],  # Only 1-3 months
            otm_min=-100,
            otm_max=100
        )

        assert result["total_found"] == 1
        assert 31 <= result["results"][0]["days_to_expiration"] <= 90

    @patch('screener.get_options_chain')
    def test_handles_api_error(self, mock_chain):
        """Should handle API errors gracefully"""
        mock_chain.return_value = {
            "results": [],
            "underlying_price": None,
            "error": "API error: Rate limit exceeded"
        }

        result = screen_options(
            tickers=["AAPL"],
            max_price=0.05,
            contract_type="call",
            expiration_ranges=["1-3m"],
            otm_min=0,
            otm_max=10
        )

        assert result["total_found"] == 0
        assert len(result["errors"]) == 1
        assert "AAPL" in result["errors"][0]["ticker"]

    @patch('screener.get_options_chain')
    def test_handles_missing_data(self, mock_chain):
        """Should skip options with missing critical data"""
        mock_chain.return_value = {
            "results": [
                {
                    "details": {
                        "ticker": "O:AAPL250221C00105000",
                        "strike_price": 105,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.02}
                },
                {
                    "details": {
                        "ticker": "O:AAPL250221C00110000",
                        "strike_price": None,  # Missing strike
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.02}
                },
                {
                    "details": {
                        "ticker": "O:AAPL250221C00115000",
                        "strike_price": 115,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {}  # Missing price
                }
            ],
            "underlying_price": 100
        }

        result = screen_options(
            tickers=["AAPL"],
            max_price=0.10,
            contract_type="call",
            expiration_ranges=["1-3m"],
            otm_min=-100,
            otm_max=100
        )

        # Only the first option should pass (others have missing data)
        assert result["total_found"] == 1

    @patch('screener.get_options_chain')
    def test_multiple_tickers(self, mock_chain):
        """Should process multiple tickers"""
        def mock_chain_response(ticker, contract_type=None):
            return {
                "results": [
                    {
                        "details": {
                            "ticker": f"O:{ticker}250221C00105000",
                            "strike_price": 105,
                            "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                            "contract_type": "call"
                        },
                        "last_trade": {"price": 0.02}
                    }
                ],
                "underlying_price": 100
            }

        mock_chain.side_effect = mock_chain_response

        result = screen_options(
            tickers=["AAPL", "TSLA", "NVDA"],
            max_price=0.10,
            contract_type="call",
            expiration_ranges=["1-3m"],
            otm_min=-100,
            otm_max=100
        )

        assert result["total_found"] == 3
        tickers = [r["underlying_ticker"] for r in result["results"]]
        assert "AAPL" in tickers
        assert "TSLA" in tickers
        assert "NVDA" in tickers

    @patch('screener.get_options_chain')
    def test_results_sorted_by_price(self, mock_chain):
        """Results should be sorted by last_price ascending"""
        mock_chain.return_value = {
            "results": [
                {
                    "details": {
                        "ticker": "O:AAPL250221C00105000",
                        "strike_price": 105,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.04}
                },
                {
                    "details": {
                        "ticker": "O:AAPL250221C00106000",
                        "strike_price": 106,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.01}
                },
                {
                    "details": {
                        "ticker": "O:AAPL250221C00107000",
                        "strike_price": 107,
                        "expiration_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "contract_type": "call"
                    },
                    "last_trade": {"price": 0.02}
                }
            ],
            "underlying_price": 100
        }

        result = screen_options(
            tickers=["AAPL"],
            max_price=0.10,
            contract_type="call",
            expiration_ranges=["1-3m"],
            otm_min=-100,
            otm_max=100
        )

        prices = [r["last_price"] for r in result["results"]]
        assert prices == [0.01, 0.02, 0.04]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
