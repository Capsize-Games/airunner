import unittest
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from airunner.data.session_manager import session_scope, Session as SessionClass, engine


class TestSessionManager(unittest.TestCase):
    """Test cases for database session management."""

    def test_session_class_exists(self):
        """Test that the Session class is properly configured."""
        self.assertIsNotNone(SessionClass)
        # Check that Session is callable (creates a session)
        session = SessionClass()
        self.assertIsInstance(session, Session)
        session.close()

    def test_engine_exists(self):
        """Test that the database engine is properly configured."""
        self.assertIsNotNone(engine)
        # Verify engine has expected attributes
        self.assertTrue(hasattr(engine, 'connect'))
        self.assertTrue(hasattr(engine, 'dispose'))
        
    @patch('airunner.data.session_manager.Session')
    def test_session_scope_normal_execution(self, mock_session):
        """Test the session_scope context manager with normal execution."""
        # Set up mocks
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # Use the context manager
        with session_scope() as session:
            # Verify session is the mock and that we can use it
            self.assertEqual(session, mock_session_instance)
            session.query()  # Do something with the session
        
        # Verify the expected methods were called
        mock_session.assert_called_once()
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.close.assert_called_once()
        mock_session_instance.rollback.assert_not_called()

    @patch('airunner.data.session_manager.Session')
    def test_session_scope_with_exception(self, mock_session):
        """Test the session_scope context manager when an exception occurs."""
        # Set up mocks
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # Use the context manager with an exception
        with self.assertRaises(ValueError):
            with session_scope() as session:
                # Do something that raises an exception
                raise ValueError("Test exception")
        
        # Verify the expected methods were called
        mock_session.assert_called_once()
        mock_session_instance.commit.assert_not_called()
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.close.assert_called_once()

    @patch('airunner.data.session_manager.Session')
    def test_session_scope_cleanup_on_exception_in_commit(self, mock_session):
        """Test that session is cleaned up even when commit fails."""
        # Set up mocks
        mock_session_instance = MagicMock()
        mock_session_instance.commit.side_effect = Exception("Commit failed")
        mock_session.return_value = mock_session_instance
        
        # Use the context manager expecting an exception
        with self.assertRaises(Exception):
            with session_scope() as session:
                pass  # Normal execution, but commit will fail
        
        # Verify the expected methods were called
        mock_session.assert_called_once()
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.rollback.assert_called_once()
        mock_session_instance.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()