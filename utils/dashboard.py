#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard for ScraperMVP monitoring

This module provides a simple web-based dashboard for monitoring the ScraperMVP system.
It visualizes metrics collected by the monitoring system and shows system health status.
"""

import os
import json
import pandas as pd
import numpy as np
import datetime
import glob
from typing import Dict, List, Any, Optional, Union
import logging
from pathlib import Path
import argparse
import webbrowser
import threading

# Optional imports with fallbacks for simple vs. advanced dashboard
try:
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output, State
    import plotly.express as px
    import plotly.graph_objects as go
    from dash.exceptions import PreventUpdate
    ADVANCED_DASHBOARD = True
except ImportError:
    import http.server
    import socketserver
    ADVANCED_DASHBOARD = False

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class MetricsManager:
    """
    Manager for loading and processing metrics from JSON files.
    """
    def __init__(self, metrics_dir: str):
        """
        Initialize the metrics manager.
        
        Args:
            metrics_dir: Directory containing metrics JSON files
        """
        self.metrics_dir = metrics_dir
        self.metrics_files = []
        self.metrics_data = []
        self.latest_metrics = None
    
    def scan_metrics_files(self) -> List[str]:
        """
        Scan for metrics files in the metrics directory.
        
        Returns:
            List of metrics file paths
        """
        if not os.path.exists(self.metrics_dir):
            logger.warning(f"Metrics directory not found: {self.metrics_dir}")
            return []
        
        # Find all JSON files in the metrics directory
        pattern = os.path.join(self.metrics_dir, "*.json")
        files = glob.glob(pattern)
        
        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        
        self.metrics_files = files
        return files
    
    def load_metrics(self, max_files: int = 50) -> List[Dict[str, Any]]:
        """
        Load metrics from JSON files.
        
        Args:
            max_files: Maximum number of files to load
            
        Returns:
            List of metrics data dictionaries
        """
        files = self.scan_metrics_files()
        
        # Limit the number of files to avoid overloading memory
        files = files[:max_files]
        
        metrics_data = []
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Add file metadata
                data['_file'] = os.path.basename(file_path)
                data['_mtime'] = os.path.getmtime(file_path)
                
                metrics_data.append(data)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading metrics file {file_path}: {str(e)}")
        
        self.metrics_data = metrics_data
        
        # Set latest metrics
        if metrics_data:
            self.latest_metrics = metrics_data[0]
        
        return metrics_data
    
    def get_metrics_dataframe(self) -> Optional[pd.DataFrame]:
        """
        Convert metrics data to a pandas DataFrame.
        
        Returns:
            DataFrame with metrics data or None if no data available
        """
        if not self.metrics_data:
            return None
        
        # Flatten metrics dictionaries
        flattened_data = []
        for metrics in self.metrics_data:
            flat_metrics = self._flatten_dict(metrics)
            flattened_data.append(flat_metrics)
        
        # Create DataFrame
        df = pd.DataFrame(flattened_data)
        
        # Convert timestamps to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
        """
        Flatten a nested dictionary.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key for nested dictionaries
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Calculate system health metrics.
        
        Returns:
            Dictionary with health metrics
        """
        health = {
            "status": "Unknown",
            "last_update": None,
            "metrics_count": len(self.metrics_data),
            "scraper_success_rate": None,
            "error_count": None,
            "resource_usage": {}
        }
        
        if not self.latest_metrics:
            health["status"] = "No data available"
            return health
        
        # Get timestamp of latest metrics
        if 'timestamp' in self.latest_metrics:
            health["last_update"] = self.latest_metrics['timestamp']
        
        # Calculate success rate
        if 'counters' in self.latest_metrics:
            counters = self.latest_metrics['counters']
            
            # Find scraper success and failure counters
            success_keys = [k for k in counters.keys() if 'success' in k.lower()]
            failure_keys = [k for k in counters.keys() if 'failure' in k.lower() or 'error' in k.lower()]
            
            total_success = sum(counters.get(k, 0) for k in success_keys)
            total_failure = sum(counters.get(k, 0) for k in failure_keys)
            
            if total_success + total_failure > 0:
                success_rate = total_success / (total_success + total_failure) * 100
                health["scraper_success_rate"] = success_rate
                
                # Set status based on success rate
                if success_rate >= 90:
                    health["status"] = "Healthy"
                elif success_rate >= 70:
                    health["status"] = "Warning"
                else:
                    health["status"] = "Critical"
            
            # Get error count
            error_keys = [k for k in counters.keys() if 'error' in k.lower()]
            health["error_count"] = sum(counters.get(k, 0) for k in error_keys)
        
        # Get resource usage
        if 'gauges' in self.latest_metrics:
            gauges = self.latest_metrics['gauges']
            
            # Find CPU and memory gauges
            cpu_keys = [k for k in gauges.keys() if 'cpu' in k.lower()]
            memory_keys = [k for k in gauges.keys() if 'memory' in k.lower() or 'mem' in k.lower()]
            disk_keys = [k for k in gauges.keys() if 'disk' in k.lower()]
            
            if cpu_keys:
                health["resource_usage"]["cpu"] = gauges[cpu_keys[0]]
            
            if memory_keys:
                health["resource_usage"]["memory"] = gauges[memory_keys[0]]
            
            if disk_keys:
                health["resource_usage"]["disk"] = gauges[disk_keys[0]]
        
        return health

# Simple HTML template for basic dashboard
BASIC_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ScraperMVP Monitoring Dashboard</title>
    <meta http-equiv="refresh" content="60">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0;
            color: #333;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 16px;
            font-weight: bold;
            color: white;
        }
        .status-healthy {
            background-color: #4caf50;
        }
        .status-warning {
            background-color: #ff9800;
        }
        .status-critical {
            background-color: #f44336;
        }
        .status-unknown {
            background-color: #9e9e9e;
        }
        .card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            padding: 16px;
        }
        .card h2 {
            margin-top: 0;
            margin-bottom: 16px;
            color: #555;
            font-size: 18px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .metric {
            padding: 12px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }
        .metric-title {
            font-size: 14px;
            color: #777;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .metric-unit {
            font-size: 14px;
            color: #777;
            margin-left: 4px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        table th, table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        table th {
            background-color: #f9f9f9;
            color: #555;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #777;
            font-size: 14px;
        }
        .timestamp {
            font-style: italic;
            color: #888;
            font-size: 14px;
        }
        .chart {
            width: 100%;
            height: 300px;
            background-color: #f9f9f9;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
        .chart-placeholder {
            color: #777;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ScraperMVP Monitoring Dashboard</h1>
            <div class="status-badge status-{{ status_class }}">{{ status }}</div>
        </div>
        
        <div class="card">
            <h2>System Health</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-title">Success Rate</div>
                    <div class="metric-value">{{ success_rate }}<span class="metric-unit">%</span></div>
                </div>
                <div class="metric">
                    <div class="metric-title">Error Count</div>
                    <div class="metric-value">{{ error_count }}</div>
                </div>
                <div class="metric">
                    <div class="metric-title">CPU Usage</div>
                    <div class="metric-value">{{ cpu_usage }}<span class="metric-unit">%</span></div>
                </div>
                <div class="metric">
                    <div class="metric-title">Memory Usage</div>
                    <div class="metric-value">{{ memory_usage }}<span class="metric-unit">MB</span></div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Scraper Performance</h2>
            <div class="chart">
                <div class="chart-placeholder">
                    For interactive charts, install dash, plotly and their dependencies:
                    <br>
                    <code>pip install dash plotly pandas numpy</code>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Scraper</th>
                        <th>Success</th>
                        <th>Failure</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {{ scraper_rows }}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>Recent Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {{ metric_rows }}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p class="timestamp">Last updated: {{ timestamp }}</p>
            <p>ScraperMVP Monitoring Dashboard</p>
        </div>
    </div>
</body>
</html>
"""

class BasicDashboard:
    """
    Simple HTML dashboard for when advanced dependencies aren't available.
    """
    def __init__(self, metrics_manager: MetricsManager, output_dir: str):
        """
        Initialize the basic dashboard.
        
        Args:
            metrics_manager: Manager for metrics data
            output_dir: Directory to output HTML files
        """
        self.metrics_manager = metrics_manager
        self.output_dir = output_dir
        self.server = None
        self.port = 8050
        
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_dashboard(self) -> str:
        """
        Generate the dashboard HTML.
        
        Returns:
            Path to the generated HTML file
        """
        # Load metrics
        self.metrics_manager.load_metrics()
        
        # Get system health
        health = self.metrics_manager.get_system_health()
        
        # Generate HTML
        html = BASIC_DASHBOARD_TEMPLATE
        
        # Replace status
        status = health["status"]
        status_class = status.lower() if status in ["Healthy", "Warning", "Critical"] else "unknown"
        html = html.replace("{{ status }}", status)
        html = html.replace("{{ status_class }}", status_class)
        
        # Replace health metrics
        success_rate = f"{health['scraper_success_rate']:.1f}" if health['scraper_success_rate'] is not None else "N/A"
        error_count = str(health['error_count']) if health['error_count'] is not None else "N/A"
        cpu_usage = f"{health['resource_usage'].get('cpu', 'N/A')}"
        memory_usage = f"{health['resource_usage'].get('memory', 'N/A')}"
        
        html = html.replace("{{ success_rate }}", success_rate)
        html = html.replace("{{ error_count }}", error_count)
        html = html.replace("{{ cpu_usage }}", cpu_usage)
        html = html.replace("{{ memory_usage }}", memory_usage)
        
        # Replace timestamp
        timestamp = health["last_update"] if health["last_update"] else datetime.datetime.now().isoformat()
        html = html.replace("{{ timestamp }}", timestamp)
        
        # Generate scraper rows
        scraper_rows = ""
        if self.metrics_manager.latest_metrics and 'counters' in self.metrics_manager.latest_metrics:
            counters = self.metrics_manager.latest_metrics['counters']
            
            # Find scraper success and failure counters
            scrapers = {}
            for key in counters.keys():
                if '.success' in key and 'scraper.' in key:
                    scraper_name = key.split('.')[1]
                    if scraper_name not in scrapers:
                        scrapers[scraper_name] = {'success': 0, 'failure': 0}
                    scrapers[scraper_name]['success'] = counters[key]
                
                if '.failure' in key and 'scraper.' in key:
                    scraper_name = key.split('.')[1]
                    if scraper_name not in scrapers:
                        scrapers[scraper_name] = {'success': 0, 'failure': 0}
                    scrapers[scraper_name]['failure'] = counters[key]
            
            # Generate table rows
            for scraper, stats in scrapers.items():
                success = stats['success']
                failure = stats['failure']
                total = success + failure
                success_rate = f"{(success / total * 100):.1f}%" if total > 0 else "N/A"
                
                scraper_rows += f"<tr><td>{scraper}</td><td>{success}</td><td>{failure}</td><td>{success_rate}</td></tr>"
        
        if not scraper_rows:
            scraper_rows = "<tr><td colspan='4'>No scraper data available</td></tr>"
        
        html = html.replace("{{ scraper_rows }}", scraper_rows)
        
        # Generate metric rows
        metric_rows = ""
        if self.metrics_manager.latest_metrics:
            # Show up to 20 interesting metrics
            metrics_to_show = []
            
            # Add counters
            if 'counters' in self.metrics_manager.latest_metrics:
                counters = self.metrics_manager.latest_metrics['counters']
                for key, value in counters.items():
                    if key.startswith('app.') or key.startswith('scraper.'):
                        metrics_to_show.append((key, value))
            
            # Add gauges
            if 'gauges' in self.metrics_manager.latest_metrics:
                gauges = self.metrics_manager.latest_metrics['gauges']
                for key, value in gauges.items():
                    metrics_to_show.append((key, value))
            
            # Sort by name and limit
            metrics_to_show.sort(key=lambda x: x[0])
            metrics_to_show = metrics_to_show[:20]
            
            # Generate table rows
            for key, value in metrics_to_show:
                metric_rows += f"<tr><td>{key}</td><td>{value}</td></tr>"
        
        if not metric_rows:
            metric_rows = "<tr><td colspan='2'>No metrics available</td></tr>"
        
        html = html.replace("{{ metric_rows }}", metric_rows)
        
        # Write to file
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"dashboard_{timestamp_str}.html")
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        # Also write to index.html for consistency
        index_path = os.path.join(self.output_dir, "index.html")
        with open(index_path, 'w') as f:
            f.write(html)
        
        return index_path
    
    def start_server(self) -> None:
        """
        Start a simple HTTP server to serve the dashboard.
        """
        class DashboardHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=self.output_dir, **kwargs)
        
        # Generate dashboard initially
        self.generate_dashboard()
        
        # Start server
        try:
            with socketserver.TCPServer(("", self.port), DashboardHandler) as httpd:
                logger.info(f"Server started at http://localhost:{self.port}")
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.warning(f"Port {self.port} is already in use, trying another port")
                self.port += 1
                self.start_server()
            else:
                raise
    
    def open_dashboard(self) -> None:
        """
        Open the dashboard in a web browser.
        """
        url = f"http://localhost:{self.port}"
        webbrowser.open(url)

class AdvancedDashboard:
    """
    Interactive dashboard using Dash and Plotly.
    """
    def __init__(self, metrics_manager: MetricsManager):
        """
        Initialize the advanced dashboard.
        
        Args:
            metrics_manager: Manager for metrics data
        """
        self.metrics_manager = metrics_manager
        self.app = None
        self.update_interval = 60  # seconds
    
    def create_app(self) -> dash.Dash:
        """
        Create the Dash application.
        
        Returns:
            Dash application instance
        """
        # Create Dash app
        app = dash.Dash(__name__, title="ScraperMVP Monitoring Dashboard")
        
        # Define layout
        app.layout = html.Div([
            # Header
            html.Div([
                html.H1("ScraperMVP Monitoring Dashboard"),
                html.Div(id="status-badge", className="status-badge")
            ], className="header"),
            
            # System Health Card
            html.Div([
                html.H2("System Health"),
                html.Div([
                    html.Div([
                        html.Div("Success Rate", className="metric-title"),
                        html.Div([
                            html.Span(id="success-rate", className="metric-value"),
                            html.Span("%", className="metric-unit")
                        ], className="metric-value-container")
                    ], className="metric"),
                    html.Div([
                        html.Div("Error Count", className="metric-title"),
                        html.Div(id="error-count", className="metric-value")
                    ], className="metric"),
                    html.Div([
                        html.Div("CPU Usage", className="metric-title"),
                        html.Div([
                            html.Span(id="cpu-usage", className="metric-value"),
                            html.Span("%", className="metric-unit")
                        ], className="metric-value-container")
                    ], className="metric"),
                    html.Div([
                        html.Div("Memory Usage", className="metric-title"),
                        html.Div([
                            html.Span(id="memory-usage", className="metric-value"),
                            html.Span("MB", className="metric-unit")
                        ], className="metric-value-container")
                    ], className="metric")
                ], className="metrics-grid")
            ], className="card"),
            
            # Scraper Performance Card
            html.Div([
                html.H2("Scraper Performance"),
                # Success rate chart
                dcc.Graph(id="success-rate-chart"),
                # Scraper stats table
                html.Div(id="scraper-stats-table")
            ], className="card"),
            
            # Recent Requests Card
            html.Div([
                html.H2("Recent Operations"),
                dcc.Graph(id="requests-chart")
            ], className="card"),
            
            # Resource Usage Card
            html.Div([
                html.H2("Resource Usage"),
                dcc.Graph(id="resource-usage-chart")
            ], className="card"),
            
            # Data Quality Card
            html.Div([
                html.H2("Data Quality"),
                dcc.Graph(id="data-quality-chart")
            ], className="card"),
            # Hidden store for health data
            html.Div(id="health-data-store", style={"display": "none"}),
            # Interval for refreshing metrics
            dcc.Interval(id="interval-component", interval=self.update_interval*1000, n_intervals=0),
            # Footer
            html.Div([
                html.P(id="timestamp", className="timestamp"),
                html.P("ScraperMVP Monitoring Dashboard")
            ], className="footer"),
            
        ], className="container")
        
        # Define callbacks
        @app.callback(
            [Output("health-data-store", "children")],
            [Input("interval-component", "n_intervals")]
        )
        def update_metrics(_n):
            """
            Update metrics data.
            
            Args:
                _n: Interval component counter (unused)
                
            Returns:
                JSON string with health data
            """
            # Load metrics
            self.metrics_manager.load_metrics()
            
            # Get system health
            health = self.metrics_manager.get_system_health()
            
            # Return as JSON string
            return [json.dumps(health)]
        
        @app.callback(
            [
                Output("status-badge", "children"),
                Output("status-badge", "className"),
                Output("success-rate", "children"),
                Output("error-count", "children"),
                Output("cpu-usage", "children"),
                Output("memory-usage", "children"),
                Output("timestamp", "children")
            ],
            [Input("health-data-store", "children")]
        )
        def update_health_display(health_json_list):
            """
            Update health display components.
            
            Args:
                health_json: JSON string with health data
                
            Returns:
                Values for display components
            """
            if not health_json_list or not health_json_list[0]:
                # Provide default/empty values for all 7 outputs
                return "Unknown", "status-badge status-unknown", "N/A", "N/A", "N/A", "N/A", f"Last updated: {datetime.datetime.now().isoformat()}"

            try:
                health = json.loads(health_json_list[0])
            except json.JSONDecodeError:
                return "Error", "status-badge status-critical", "N/A", "N/A", "N/A", "N/A", f"Last updated: {datetime.datetime.now().isoformat()} (JSON error)"

            status = health.get("status", "Unknown")
            status_class = f"status-badge status-{status.lower()}" if status in ["Healthy", "Warning", "Critical"] else "status-badge status-unknown"
            
            scraper_success_rate = health.get('scraper_success_rate')
            success_rate_display = f"{scraper_success_rate:.1f}" if scraper_success_rate is not None else "N/A"
            
            error_count_val = health.get('error_count')
            error_count_display = str(error_count_val) if error_count_val is not None else "N/A"
            
            resource_usage = health.get('resource_usage', {})
            cpu_usage = f"{resource_usage.get('cpu', 'N/A')}"
            memory_usage = f"{resource_usage.get('memory', 'N/A')}" # Assuming memory is in MB as per original unit
            
            timestamp_str = health.get('last_update')
            timestamp_display = f"Last updated: {timestamp_str}" if timestamp_str else f"Last updated: {datetime.datetime.now().isoformat()}"
            
            return status, status_class, success_rate_display, error_count_display, cpu_usage, memory_usage, timestamp_display
        
        @app.callback(
            Output("success-rate-chart", "figure"),
            [Input("health-data-store", "children")]
        )
        def update_success_rate_chart(health_json_list):
            """
            Update success rate chart.
            
            Args:
                health_json: JSON string with health data
                
            Returns:
                Plotly figure for success rate chart
            """
            if not health_json_list or not health_json_list[0]:
                return px.bar(title="Scraper Success Rates - No Data Available")

            df = self.metrics_manager.get_metrics_dataframe()

            if df is None or df.empty:
                return px.bar(title="Scraper Success Rates - No Data Available")

            success_cols = [col for col in df.columns if '.success' in col and 'counters.scraper' in col]
            failure_cols = [col for col in df.columns if '.failure' in col and 'counters.scraper' in col]

            scraper_names = set()
            for col in success_cols + failure_cols:
                parts = col.split('.')
                if len(parts) > 2 and parts[0] == 'counters' and parts[1] == 'scraper':
                    scraper_names.add(parts[2])
            
            scrapers = sorted(list(scraper_names))

            if not scrapers:
                 return px.bar(title="Scraper Success Rates - No Scraper Data")

            chart_data = []
            # Use the last row of the DataFrame for current snapshot values
            current_row = df.iloc[-1] if not df.empty else None

            if current_row is None:
                return px.bar(title="Scraper Success Rates - No Current Data")

            for scraper_name in scrapers:
                success_col_name = f"counters.scraper.{scraper_name}.success"
                failure_col_name = f"counters.scraper.{scraper_name}.failure"
                
                success = 0
                failure = 0

                if success_col_name in df.columns and pd.notna(current_row[success_col_name]):
                    success = current_row[success_col_name]
                if failure_col_name in df.columns and pd.notna(current_row[failure_col_name]):
                    failure = current_row[failure_col_name]
                
                total = success + failure
                success_rate_val = (success / total * 100) if total > 0 else 0.0
                
                chart_data.append({
                    "Scraper": scraper_name,
                    "Success Rate": success_rate_val,
                    "Total Operations": total
                })
            
            if not chart_data:
                return px.bar(title="Scraper Success Rates - No Data to Display")

            fig = px.bar(
                chart_data,
                x="Scraper",
                y="Success Rate",
                title="Scraper Success Rates",
                text="Success Rate",
                color="Success Rate",
                color_continuous_scale=["red", "orange", "green"],
                range_color=[0, 100],
                hover_data=["Total Operations"]
            )
            
            fig.update_layout(
                yaxis_title="Success Rate (%)",
                coloraxis_showscale=False
            )
            
            fig.update_traces(
                texttemplate="%{y:.1f}%",
                textposition="outside"
            )
            
            return fig
        
        @app.callback(
            Output("scraper-stats-table", "children"),
            [Input("health-data-store", "children")]
        )
        def update_scraper_stats_table(health_json_list):
            """
            Update scraper stats table.
            
            Args:
                health_json: JSON string with health data
                
            Returns:
                HTML table for scraper stats
            """
            if not health_json_list or not health_json_list[0]:
                raise PreventUpdate
            
            if not self.metrics_manager.latest_metrics or 'counters' not in self.metrics_manager.latest_metrics:
                return html.Div("No scraper data available")
            
            counters = self.metrics_manager.latest_metrics['counters']
            scrapers_stats = {}

            for key, value in counters.items():
                parts = key.split('.')
                if len(parts) == 4 and parts[0] == 'counters' and parts[1] == 'scraper':
                    scraper_name = parts[2]
                    metric_type = parts[3] # 'success' or 'failure'

                    if scraper_name not in scrapers_stats:
                        scrapers_stats[scraper_name] = {'success': 0, 'failure': 0}
                    
                    if metric_type == 'success':
                        scrapers_stats[scraper_name]['success'] = int(value) if pd.notna(value) else 0
                    elif metric_type == 'failure':
                        scrapers_stats[scraper_name]['failure'] = int(value) if pd.notna(value) else 0
            
            if not scrapers_stats:
                return html.Div("No scraper statistics available.")

            table_body = []
            for scraper_name, stats_data in scrapers_stats.items(): # Renamed stats to stats_data
                s = stats_data['success']
                f = stats_data['failure']
                total = s + f
                rate = f"{(s / total * 100):.1f}%" if total > 0 else "N/A"
                table_body.append(html.Tr([
                    html.Td(scraper_name),
                    html.Td(s),
                    html.Td(f),
                    html.Td(rate)
                ]))

            return html.Table([
                html.Thead(html.Tr([html.Th("Scraper"), html.Th("Success"), html.Th("Failure"), html.Th("Success Rate")])),
                html.Tbody(table_body)
            ])
        
        @app.callback(
            Output("requests-chart", "figure"),
            [Input("health-data-store", "children")]
        )
        def update_requests_chart(health_json_list): # Renamed for consistency
            if not health_json_list or not health_json_list[0]:
                return px.line(title="Recent Operations - No Data Available")
            
            df = self.metrics_manager.get_metrics_dataframe()
            
            if df is None or df.empty or 'timestamp' not in df.columns:
                return px.line(title="Recent Operations - No Data Available")
            
            request_cols = [col for col in df.columns if 'requests' in col and 'counters.scraper' in col]
            
            if not request_cols:
                return px.line(title="Recent Operations - No Request Data Available")
            
            chart_data = []
            for timestamp_idx, timestamp_val in enumerate(df['timestamp']): # Renamed for clarity
                for col in request_cols:
                    if timestamp_idx < len(df) and col in df.columns and pd.notna(df[col].iloc[timestamp_idx]):
                        value = df[col].iloc[timestamp_idx]
                        parts = col.split('.')
                        # e.g. counters.scraper.google_maps.requests -> google_maps_requests
                        name = f"{parts[2]}_{parts[3]}" if len(parts) >= 4 and parts[1] == 'scraper' else col
                        chart_data.append({
                            "Timestamp": timestamp_val,
                            "Metric": name,
                            "Value": value
                        })
            
            if not chart_data:
                return px.line(title="Recent Operations - No Data to Display")

            fig = px.line(
                chart_data,
                x="Timestamp",
                y="Value",
                color="Metric",
                title="Recent Operations"
            )
            
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Count",
                legend_title="Operation Type"
            )
            
            return fig
        
        @app.callback(
            Output("resource-usage-chart", "figure"),
            [Input("health-data-store", "children")]
        )
        def update_resource_chart(health_json_list): # Renamed for consistency
            if not health_json_list or not health_json_list[0]:
                return px.line(title="Resource Usage - No Data Available")
            
            df = self.metrics_manager.get_metrics_dataframe()
            
            if df is None or df.empty or 'timestamp' not in df.columns:
                return px.line(title="Resource Usage - No Data Available")
            
            cpu_cols = [col for col in df.columns if 'cpu' in col.lower() and 'gauges' in col]
            memory_cols = [col for col in df.columns if ('memory' in col.lower() or 'mem' in col.lower()) and 'gauges' in col]
            disk_cols = [col for col in df.columns if 'disk' in col.lower() and 'gauges' in col]
            resource_cols = cpu_cols + memory_cols + disk_cols
            
            if not resource_cols:
                return px.line(title="Resource Usage - No Resource Metric Data Available")
            
            chart_data = []
            for timestamp_idx, timestamp_val in enumerate(df['timestamp']): # Renamed for clarity
                for col in resource_cols:
                    if timestamp_idx < len(df) and col in df.columns and pd.notna(df[col].iloc[timestamp_idx]):
                        value = df[col].iloc[timestamp_idx]
                        # e.g., gauges.system.cpu_usage -> system_cpu_usage
                        # e.g., gauges.system.memory_usage_mb -> system_memory_usage_mb
                        parts = col.split('.')
                        name = '_'.join(parts[1:]) if len(parts) > 1 else col # Joins all parts after 'gauges'
                        chart_data.append({
                            "Timestamp": timestamp_val,
                            "Metric": name,
                            "Value": value
                        })

            if not chart_data:
                return px.line(title="Resource Usage - No Data to Display")
            # ... (rest of fig creation and layout)
            fig = px.line(
                chart_data,
                x="Timestamp",
                y="Value",
                color="Metric",
                title="Resource Usage Over Time"
            )
            
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Value",
                legend_title="Resource Metric"
            )
            
            return fig
        
        @app.callback(
            Output("data-quality-chart", "figure"),
            [Input("health-data-store", "children")]
        )
        def update_data_quality_chart(health_json_list): # Renamed for consistency
            if not health_json_list or not health_json_list[0]:
                return px.bar(title="Data Quality Metrics - No Data Available") # Changed to px.bar for consistency if it's a bar chart
            
            df = self.metrics_manager.get_metrics_dataframe()
            
            if df is None or df.empty or 'timestamp' not in df.columns: # Added timestamp check for line chart
                return px.line(title="Data Quality Metrics - No Data Available") # Assuming line chart from original
            
            # Original: quality_cols = [col for col in df.columns if 'data_quality' in col.lower() and ('score' in col.lower() or 'completeness' in col.lower())]
            # This might pick up gauges.data_quality.SOURCE.METRIC_NAME
            quality_cols = [col for col in df.columns if 'gauges.data_quality' in col.lower()]


            if not quality_cols:
                return px.line(title="Data Quality Metrics - No Quality Metric Data Available")
            
            chart_data = []
            for timestamp_idx, timestamp_val in enumerate(df['timestamp']): # Renamed for clarity
                for col in quality_cols:
                    if timestamp_idx < len(df) and col in df.columns and pd.notna(df[col].iloc[timestamp_idx]):
                        value = df[col].iloc[timestamp_idx]
                        # e.g. gauges.data_quality.google_maps.score -> google_maps_score
                        # e.g. gauges.data_quality.overall.completeness -> overall_completeness
                        parts = col.split('.')
                        name = f"{parts[2]}_{parts[3]}" if len(parts) >= 4 and parts[1] == 'data_quality' else col
                        chart_data.append({
                            "Timestamp": timestamp_val,
                            "Metric": name,
                            "Value": value
                        })
            
            if not chart_data:
                return px.line(title="Data Quality Metrics - No Data to Display")

            fig = px.line( # Assuming it's a line chart as per original variable name
                chart_data,
                x="Timestamp",
                y="Value",
                color="Metric",
                title="Data Quality Metrics Over Time"
            )
            # ... (rest of fig layout)
            return fig
        
        # CSS for Dash app
        app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 20px;
                    }
                    .header h1 {
                        margin: 0;
                        color: #333;
                    }
                    .status-badge {
                        padding: 8px 16px;
                        border-radius: 16px;
                        font-weight: bold;
                        color: white;
                    }
                    .status-healthy {
                        background-color: #4caf50;
                    }
                    .status-warning {
                        background-color: #ff9800;
                    }
                    .status-critical {
                        background-color: #f44336;
                    }
                    .status-unknown {
                        background-color: #9e9e9e;
                    }
                    .card {
                        background-color: white;
                        border-radius: 8px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        margin-bottom: 20px;
                        padding: 16px;
                    }
                    .card h2 {
                        margin-top: 0;
                        margin-bottom: 16px;
                        color: #555;
                        font-size: 18px;
                    }
                    .metrics-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                        gap: 20px;
                    }
                    .metric {
                        padding: 12px;
                        background-color: #f9f9f9;
                        border-radius: 4px;
                    }
                    .metric-title {
                        font-size: 14px;
                        color: #777;
                        margin-bottom: 8px;
                    }
                    .metric-value {
                        font-size: 24px;
                        font-weight: bold;
                        color: #333;
                    }
                    .metric-unit {
                        font-size: 14px;
                        color: #777;
                        margin-left: 4px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    table th, table td {
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #eee;
                    }
                    table th {
                        background-color: #f9f9f9;
                        color: #555;
                    }
                    .footer {
                        text-align: center;
                        margin-top: 40px;
                        color: #777;
                        font-size: 14px;
                    }
                    .timestamp {
                        font-style: italic;
                        color: #888;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
        
        self.app = app
        return app
    
    def start_dashboard(self, host: str = "0.0.0.0", port: int = 8050, debug: bool = False) -> None:
        """
        Start the dashboard.
        
        Args:
            host: Host address to bind to
            port: Port to run the server on
            debug: Whether to run in debug mode
        """
        if self.app is None:
            self.create_app()

        # Dash v2+: use run() instead of deprecated run_server()
        self.app.run(host=host, port=port, debug=debug)
    
    def open_dashboard(self, port: int = 8050) -> None:
        """
        Open the dashboard in a web browser.
        
        Args:
            port: Port the dashboard is running on
        """
        url = f"http://localhost:{port}"
        webbrowser.open(url)

def main():
    """
    Main function for running the dashboard.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ScraperMVP Monitoring Dashboard")
    parser.add_argument("--metrics-dir", help="Directory containing metrics files", default="metrics")
    parser.add_argument("--output-dir", help="Directory for dashboard output", default="dashboard")
    parser.add_argument("--port", help="Port to run the dashboard on", type=int, default=8050)
    parser.add_argument("--update-interval", help="Dashboard update interval in seconds", type=int, default=60)
    parser.add_argument("--auto-open", help="Automatically open dashboard in browser", action="store_true")
    args = parser.parse_args()
    
    # Create absolute paths
    metrics_dir = os.path.abspath(args.metrics_dir) if not os.path.isabs(args.metrics_dir) else args.metrics_dir
    output_dir = os.path.abspath(args.output_dir) if not os.path.isabs(args.output_dir) else args.output_dir
    
    # Create metrics manager
    metrics_manager = MetricsManager(metrics_dir)
    
    # Create and start dashboard
    if ADVANCED_DASHBOARD:
        logger.info("Starting advanced dashboard with Dash and Plotly")
        dashboard = AdvancedDashboard(metrics_manager)
        dashboard.create_app()
        
        if args.auto_open:
            # Open dashboard in a new thread to avoid blocking
            threading.Timer(1.0, lambda: dashboard.open_dashboard(args.port)).start()
        
        # Start dashboard server
        dashboard.start_dashboard(port=args.port)
    else:
        logger.info("Starting basic dashboard (Dash and Plotly not available)")
        dashboard = BasicDashboard(metrics_manager, output_dir)
        
        # Generate dashboard initially
        dashboard_path = dashboard.generate_dashboard()
        logger.info(f"Dashboard generated at: {dashboard_path}")
        
        if args.auto_open:
            # Open dashboard in a new thread to avoid blocking
            threading.Timer(1.0, dashboard.open_dashboard).start()
        
        # Start simple HTTP server
        dashboard.start_server()

if __name__ == "__main__":
    main()
