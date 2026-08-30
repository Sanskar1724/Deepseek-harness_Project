"""ORM models. Importing this package registers every table on Base.metadata."""
from app.models.alert import Alert, AlertDelivery  # noqa: F401
from app.models.base import TimestampMixin  # noqa: F401
from app.models.field_report import FieldReport, ReportStatus, ReportType  # noqa: F401
from app.models.infrastructure import Infrastructure, InfrastructureType  # noqa: F401
from app.models.landslide_event import LandslideEvent  # noqa: F401
from app.models.location import Location  # noqa: F401
from app.models.model_registry import ModelRegistry  # noqa: F401
from app.models.risk_prediction import RiskPrediction  # noqa: F401
from app.models.sensor import Sensor, SensorReading  # noqa: F401
from app.models.weather_data import WeatherData  # noqa: F401

__all__ = [
    "Alert",
    "AlertDelivery",
    "FieldReport",
    "Infrastructure",
    "InfrastructureType",
    "LandslideEvent",
    "Location",
    "ModelRegistry",
    "ReportStatus",
    "ReportType",
    "RiskPrediction",
    "Sensor",
    "SensorReading",
    "TimestampMixin",
    "WeatherData",
]
