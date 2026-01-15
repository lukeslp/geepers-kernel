"""
Health check utilities for Flask applications.

Provides standardized health check endpoints with optional dependency checks.
"""

from datetime import datetime
from typing import Dict, Callable, Optional
from flask import Flask, jsonify


def create_health_endpoint(
    app: Flask,
    service_name: str,
    version: str = "1.0.0",
    checks: Optional[Dict[str, Callable]] = None
):
    """
    Create a standard health check endpoint for a Flask app.

    Args:
        app: Flask application instance
        service_name: Name of the service
        version: Service version
        checks: Optional dict of dependency check functions
                {
                    "redis": lambda: redis_client.ping(),
                    "database": lambda: db.execute("SELECT 1")
                }

    Example:
        app = Flask(__name__)
        create_health_endpoint(
            app,
            "My API",
            "1.2.0",
            {"redis": lambda: redis.ping()}
        )
    """

    @app.route('/health', methods=['GET'])
    def health_check():
        """Comprehensive health check endpoint"""
        health_status = {
            "status": "healthy",
            "service": service_name,
            "version": version,
            "timestamp": datetime.now().isoformat(),
        }

        # Run dependency checks
        if checks:
            dependencies = {}
            all_healthy = True

            for name, check_func in checks.items():
                try:
                    result = check_func()
                    dependencies[name] = {
                        "status": "healthy",
                        "details": result if isinstance(result, dict) else {}
                    }
                except Exception as e:
                    all_healthy = False
                    dependencies[name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }

            health_status["dependencies"] = dependencies

            if not all_healthy:
                health_status["status"] = "degraded"

        status_code = 200 if health_status["status"] != "unhealthy" else 503

        return jsonify(health_status), status_code

    return app
