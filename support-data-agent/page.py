"""
Base page class for the Streamlit app.
"""

import streamlit as st


class BasePage:
    """Base class for all pages in the application."""

    def __init__(self):
        self.name = "base_page"

    def print_page(self):
        """Print the main content of the page. Should be overridden by subclasses."""
        st.write("This is the base page. Override print_page() in your subclass.")

    def print_sidebar(self):
        """Print the sidebar content. Can be overridden by subclasses."""
        pass
