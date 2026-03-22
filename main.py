"""
main.py — Application Entry Point

Starts the Logos AI Flask development server on port 5000.
In production, use a WSGI server like Gunicorn instead of running this directly.
"""

from app import app

if __name__ == "__main__":
    # Run in debug mode so the server auto-reloads on code changes.
    # host='0.0.0.0' makes the server accessible from outside the container
    # (required for Replit's proxied preview pane).
    app.run(host='0.0.0.0', port=5000, debug=True)
