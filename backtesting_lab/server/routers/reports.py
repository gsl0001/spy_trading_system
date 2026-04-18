"""
Reports API Router — Endpoints for performance reports and data export.
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from backtesting_lab.server.models import DailyReport, PerformanceReport, StatusResponse

router = APIRouter(prefix="/api/reports", tags=["Reports"])

# Global references (injected from main.py)
_journal = None
_report_gen = None


def set_services(journal, report_gen):
    """Inject service instances."""
    global _journal, _report_gen
    _journal = journal
    _report_gen = report_gen


@router.get("/daily")
async def get_daily_report(date: str = None):
    """Get today's (or specific date's) trade summary."""
    if _report_gen is None:
        return {"error": "Report generator not initialized"}

    return _report_gen.daily_report(date)


@router.get("/performance")
async def get_performance_report(period: str = "30d"):
    """Get performance report for a given period (e.g., 7d, 30d, 90d, 1y)."""
    if _report_gen is None:
        return {"error": "Report generator not initialized"}

    return _report_gen.performance_report(period)


@router.get("/trades")
async def get_trades(start: str = None, end: str = None,
                     strategy: str = None, source: str = None,
                     limit: int = 200):
    """Get historical trade log with optional filters."""
    if _journal is None:
        return {"trades": []}

    trades = _journal.get_trades(
        start_date=start, end_date=end,
        strategy=strategy, source=source, limit=limit
    )
    return {"trades": trades, "count": len(trades)}


@router.get("/strategies")
async def get_strategy_performance():
    """Get performance breakdown by strategy."""
    if _journal is None:
        return {"strategies": []}

    return {"strategies": _journal.get_strategy_performance()}


@router.get("/export/csv")
async def export_csv(start: str = None, end: str = None):
    """Export trades as CSV."""
    if _report_gen is None:
        return PlainTextResponse("Report generator not initialized", status_code=500)

    csv_content = _report_gen.export_csv(start_date=start, end_date=end)
    return PlainTextResponse(
        csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades_export.csv"}
    )
