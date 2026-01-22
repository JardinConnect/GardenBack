import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from services.farm_state.service import get_farm_summary
from services.farm_state.schemas import FarmStateSummary
from db.models import Area, Cell, Sensor


def test_get_farm_summary_success():
    """
    Tests that get_farm_summary correctly calculates and returns the farm summary.
    """
    # Arrange
    mock_db = Mock(spec=Session)
    
    # Mock the return value for the sensor types query
    sensor_types_data = [
        ('temperature',), ('temperature',), ('temperature',),
        ('humidity',), ('humidity',),
        ('light',)
    ]

    # Use a side_effect to return different mocks for different query arguments
    def query_side_effect(model):
        query_mock = Mock()
        if getattr(model, 'name', None) == 'sensor_type':
            query_mock.all.return_value = sensor_types_data
        elif model == Area:
            query_mock.count.return_value = 5
        elif model == Cell:
            query_mock.count.return_value = 15
        elif model == Sensor:
            query_mock.count.return_value = 30
        return query_mock

    mock_db.query.side_effect = query_side_effect

    # Act
    summary = get_farm_summary(mock_db)

    # Assert
    assert isinstance(summary, FarmStateSummary)
    assert summary.total_areas == 5
    assert summary.total_cells == 15
    assert summary.total_sensors == 30
    assert summary.sensor_types == {
        'temperature': 3,
        'humidity': 2,
        'light': 1
    }

    assert mock_db.query.call_count == 4

def test_get_farm_summary_no_data():
    """
    Tests that get_farm_summary handles the case where there is no data in the database.
    """
    # Arrange
    mock_db = Mock(spec=Session)
    
    # Use a side_effect to handle different query arguments correctly
    def query_side_effect(model):
        query_mock = Mock()
        if getattr(model, 'name', None) == 'sensor_type':
            query_mock.all.return_value = []
        elif model in [Area, Cell, Sensor]:
            query_mock.count.return_value = 0
        return query_mock

    mock_db.query.side_effect = query_side_effect

    # Act
    summary = get_farm_summary(mock_db)

    # Assert
    assert summary.total_areas == 0
    assert summary.total_cells == 0
    assert summary.total_sensors == 0
    assert summary.sensor_types == {}