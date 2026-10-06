"""
API Endpoint Tests using FastAPI TestClient.

These tests verify the API contract (response shape, status codes, error handling).
They require a running database connection — skip gracefully if not available.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestHealthCheck:

    def test_health_endpoint_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_schema(self):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAssetEndpoints:

    @patch("backend.routes.market._execute")
    def test_list_assets_returns_all(self, mock_exec):
        resp = client.get("/api/market/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert "assets" in data
        assert "count" in data
        assert data["count"] == 18   # Our universe has 18 assets

    def test_invalid_ticker_returns_404(self):
        resp = client.get("/api/market/prices/INVALID_TICKER_XYZ")
        assert resp.status_code == 404

    def test_price_days_too_small_returns_422(self):
        resp = client.get("/api/market/prices/AAPL?days=10")
        assert resp.status_code == 422   # FastAPI validation error


class TestPortfolioEndpoints:

    def test_invalid_weights_returns_422(self):
        payload = {
            "weights":        {"AAPL": 0.5, "MSFT": 0.3},   # sum = 0.8 — invalid
            "portfolio_name": "Bad Portfolio",
        }
        resp = client.post("/api/portfolio/analyse", json=payload)
        assert resp.status_code == 422

    def test_unknown_ticker_in_portfolio_returns_422(self):
        payload = {
            "weights":        {"FAKE123": 0.5, "AAPL": 0.5},
            "portfolio_name": "Test",
        }
        resp = client.post("/api/portfolio/analyse", json=payload)
        assert resp.status_code == 422

    def test_negative_weight_returns_422(self):
        payload = {
            "weights":        {"AAPL": 1.2, "MSFT": -0.2},
            "portfolio_name": "Test",
        }
        resp = client.post("/api/portfolio/analyse", json=payload)
        assert resp.status_code == 422


class TestForecastEndpoints:

    def test_invalid_ticker_returns_404(self):
        resp = client.get("/api/forecast/NOTREAL")
        assert resp.status_code == 404

    def test_horizon_out_of_range_returns_422(self):
        resp = client.get("/api/forecast/AAPL?horizon=200")
        assert resp.status_code == 422


class TestInsightsEndpoint:

    def test_insights_returns_200_without_api_key(self):
        payload = {"context": "Test sector: return 10%, vol 15%"}
        resp = client.post("/api/insights/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "insight" in data
        # Without API key, should return demo mode response
        assert data["status"] == "api_key_not_configured"
