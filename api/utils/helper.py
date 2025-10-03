from decimal import Decimal
from datetime import date, datetime


def serialize_row_datetime(row):
    return {
        key: value.isoformat() if isinstance(value, (datetime, date)) else value
        for key, value in row.items()
    }
    
def serialize_row(row):
    """
    Convert SQLAlchemy row with datetime/date/decimal to JSON serializable dict
    """
    return {
        key: (
            value.isoformat() if isinstance(value, (datetime, date))
            else float(value) if isinstance(value, Decimal)
            else value
        )
        for key, value in row.items()
    }