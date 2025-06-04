#!/usr/bin/env python3
"""Test script to check browser session functionality."""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from airunner.data.models.airunner_settings import AIRunnerSettings
from airunner.data.session_manager import session_scope
import json


def test_browser_session():
    """Test browser session data retrieval."""
    print("Testing browser session functionality...")

    with session_scope() as session:
        # Check for browser_session settings
        browser_session = (
            session.query(AIRunnerSettings)
            .filter_by(name="browser_session")
            .first()
        )
        if browser_session:
            print("Browser session found:")
            print(f"Data type: {type(browser_session.data)}")
            print(f"Data: {browser_session.data}")

            # Try to parse if it's a string
            if isinstance(browser_session.data, str):
                try:
                    parsed_data = json.loads(browser_session.data)
                    print(f"Parsed data: {parsed_data}")
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {e}")
        else:
            print("No browser session found in database")

        # Check for browser settings
        browser_settings = (
            session.query(AIRunnerSettings).filter_by(name="browser").first()
        )
        if browser_settings:
            print("\nBrowser settings found:")
            print(f"Data type: {type(browser_settings.data)}")
            if hasattr(browser_settings.data, "private_browsing"):
                print(
                    f"Private browsing: {browser_settings.data.private_browsing}"
                )
        else:
            print("\nNo browser settings found")

        # List all settings to see what's there
        all_settings = session.query(AIRunnerSettings).all()
        print(f"\nAll settings in database ({len(all_settings)} total):")
        for setting in all_settings:
            print(f"- {setting.name}")


if __name__ == "__main__":
    test_browser_session()
