import pytest
from unittest.mock import patch
from services.farm_state.service import get_farm_stats
from services.farm_state.errors import FarmStatsError
from fastapi import HTTPException


@patch('services.farm_state.repository.get_counts')
def test_get_farm_stats_success(mock_get_counts):
    """Vérifie que le service formate correctement les données du repository."""
    # Arrange
    # Simule un retour réussi du repository
    mock_get_counts.return_value = (5, 10, 20)  # (total_users, total_areas, total_cells)
    mock_db = None  # La session DB n'est plus utilisée directement par le service

    # Act
    stats = get_farm_stats(mock_db)

    # Assert
    mock_get_counts.assert_called_once_with(mock_db)
    assert stats.total_users == 5
    assert stats.total_areas == 10
    assert stats.total_cells == 20


@patch('services.farm_state.repository.get_counts')
def test_get_farm_stats_repository_error(mock_get_counts):
    """Vérifie que le service lève une FarmStatsError si le repository échoue."""
    # Arrange
    mock_get_counts.side_effect = Exception("Database connection failed")
    mock_db = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        get_farm_stats(mock_db)

    assert exc_info.value == FarmStatsError

    mock_get_counts.assert_called_once_with(mock_db)