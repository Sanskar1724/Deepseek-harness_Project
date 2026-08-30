"""initial schema (locations, weather, landslides, risk, reports, infra, sensors, alerts)

This version does NOT use SpatiaLite geometry columns. Instead, latitude and
longitude are stored as plain Float columns. Spatial queries (distance, bbox)
are computed in Python using the Haversine formula.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- locations ---
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("elevation_m", sa.Float, nullable=True),
        sa.Column("slope_deg", sa.Float, nullable=True),
        sa.Column("aspect_deg", sa.Float, nullable=True),
        sa.Column("land_cover", sa.String(80), nullable=True),
        sa.Column("ndvi", sa.Float, nullable=True),
        sa.Column("historical_landslide_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_locations_state", "locations", ["state"])
    op.create_index("ix_locations_district", "locations", ["district"])
    op.create_index("ix_locations_latitude", "locations", ["latitude"])
    op.create_index("ix_locations_longitude", "locations", ["longitude"])

    # --- weather_data ---
    op.create_table(
        "weather_data",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rainfall_1h", sa.Float, nullable=False, server_default="0"),
        sa.Column("rainfall_6h", sa.Float, nullable=False, server_default="0"),
        sa.Column("rainfall_24h", sa.Float, nullable=False, server_default="0"),
        sa.Column("rainfall_72h", sa.Float, nullable=False, server_default="0"),
        sa.Column("forecast_rainfall_24h", sa.Float, nullable=False, server_default="0"),
        sa.Column("forecast_rainfall_72h", sa.Float, nullable=False, server_default="0"),
        sa.Column("temperature_c", sa.Float, nullable=False, server_default="0"),
        sa.Column("humidity_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("soil_moisture_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("source", sa.String(40), nullable=False, server_default="mock"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_weather_data_location_id", "weather_data", ["location_id"])
    op.create_index("ix_weather_data_timestamp", "weather_data", ["timestamp"])

    # --- landslide_events ---
    op.create_table(
        "landslide_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("severity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("source", sa.String(80), nullable=False, server_default="unknown"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_landslide_events_event_date", "landslide_events", ["event_date"])

    # --- risk_predictions ---
    op.create_table(
        "risk_predictions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("feature_contributions", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_predictions_location_id", "risk_predictions", ["location_id"])
    op.create_index("ix_risk_predictions_timestamp", "risk_predictions", ["timestamp"])
    op.create_index("ix_risk_predictions_model_version", "risk_predictions", ["model_version"])

    # --- field_reports ---
    op.create_table(
        "field_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(64), nullable=False, unique=True),
        sa.Column("report_type", sa.String(24), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="RECEIVED"),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="synced"),
        sa.Column("conflict_with", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_field_reports_client_id", "field_reports", ["client_id"], unique=True)
    op.create_index("ix_field_reports_report_type", "field_reports", ["report_type"])
    op.create_index("ix_field_reports_timestamp", "field_reports", ["timestamp"])

    # --- infrastructure ---
    op.create_table(
        "infrastructure",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("importance", sa.Integer, nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_infrastructure_type", "infrastructure", ["type"])

    # --- sensors ---
    op.create_table(
        "sensors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sensor_id", sa.String(64), nullable=False, unique=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sensors_sensor_id", "sensors", ["sensor_id"], unique=True)

    # --- sensor_readings ---
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sensor_pk", sa.Integer, sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("soil_moisture", sa.Float, nullable=True),
        sa.Column("pore_pressure", sa.Float, nullable=True),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("extra", sa.String(1000), nullable=True),
    )
    op.create_index("ix_sensor_readings_sensor_pk", "sensor_readings", ["sensor_pk"])
    op.create_index("ix_sensor_readings_timestamp", "sensor_readings", ["timestamp"])

    # --- alerts ---
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("risk_prediction_id", sa.Integer, sa.ForeignKey("risk_predictions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alerts_risk_prediction_id", "alerts", ["risk_prediction_id"])
    op.create_index("ix_alerts_location_id", "alerts", ["location_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    # --- alert_deliveries ---
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.Integer, sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider_response", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_alert_deliveries_alert_id", "alert_deliveries", ["alert_id"])

    # --- model_registry ---
    op.create_table(
        "model_registry",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_version", sa.String(64), nullable=False, unique=True),
        sa.Column("algorithm", sa.String(40), nullable=False),
        sa.Column("artifact_path", sa.String(500), nullable=False),
        sa.Column("training_dataset", sa.String(200), nullable=False),
        sa.Column("metrics_json", sa.Text, nullable=False),
        sa.Column("feature_schema_json", sa.Text, nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promoted", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_registry_model_version", "model_registry", ["model_version"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_model_registry_model_version", table_name="model_registry")
    op.drop_table("model_registry")
    op.drop_index("ix_alert_deliveries_alert_id", table_name="alert_deliveries")
    op.drop_table("alert_deliveries")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_location_id", table_name="alerts")
    op.drop_index("ix_alerts_risk_prediction_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_sensor_readings_timestamp", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_sensor_pk", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_index("ix_sensors_sensor_id", table_name="sensors")
    op.drop_table("sensors")
    op.drop_index("ix_infrastructure_type", table_name="infrastructure")
    op.drop_table("infrastructure")
    op.drop_index("ix_field_reports_timestamp", table_name="field_reports")
    op.drop_index("ix_field_reports_report_type", table_name="field_reports")
    op.drop_index("ix_field_reports_client_id", table_name="field_reports")
    op.drop_table("field_reports")
    op.drop_index("ix_risk_predictions_model_version", table_name="risk_predictions")
    op.drop_index("ix_risk_predictions_timestamp", table_name="risk_predictions")
    op.drop_index("ix_risk_predictions_location_id", table_name="risk_predictions")
    op.drop_table("risk_predictions")
    op.drop_index("ix_landslide_events_event_date", table_name="landslide_events")
    op.drop_table("landslide_events")
    op.drop_index("ix_weather_data_timestamp", table_name="weather_data")
    op.drop_index("ix_weather_data_location_id", table_name="weather_data")
    op.drop_table("weather_data")
    op.drop_index("ix_locations_longitude", table_name="locations")
    op.drop_index("ix_locations_latitude", table_name="locations")
    op.drop_index("ix_locations_district", table_name="locations")
    op.drop_index("ix_locations_state", table_name="locations")
    op.drop_table("locations")
