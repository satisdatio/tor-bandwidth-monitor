"""Plugin system for extensibility."""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type, Any, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """Base class for all plugins."""
    
    name: str = "base"
    version: str = "0.0.0"
    description: str = ""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration."""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Cleanup plugin resources."""
        pass


class MetricsPlugin(PluginBase):
    """Plugin that provides additional metrics."""
    
    @abstractmethod
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect custom metrics."""
        pass


class AlertPlugin(PluginBase):
    """Plugin that provides custom alerting."""
    
    @abstractmethod
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for custom alert conditions."""
        pass


class ExportPlugin(PluginBase):
    """Plugin that exports data to external systems."""
    
    @abstractmethod
    def export(self, data: Dict[str, Any]) -> bool:
        """Export data to external system."""
        pass


class PluginManager:
    """
    Manages plugin loading and lifecycle.
    """
    
    def __init__(self, plugin_dir: str = "./plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, PluginBase] = {}
        self._metrics_plugins: List[MetricsPlugin] = []
        self._alert_plugins: List[AlertPlugin] = []
        self._export_plugins: List[ExportPlugin] = []
    
    def load_plugins(self, config: Dict[str, Any]) -> int:
        """
        Load all plugins from plugin directory.
        
        Returns:
            Number of successfully loaded plugins
        """
        if not self.plugin_dir.exists():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return 0
        
        loaded = 0
        
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                module_name = f"plugins.{plugin_file.stem}"
                spec = importlib.util.spec_from_file_location(
                    module_name, plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find plugin classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, PluginBase) and obj != PluginBase:
                        plugin = obj()
                        if plugin.initialize(config.get(plugin.name, {})):
                            self.plugins[plugin.name] = plugin
                            self._register_plugin(plugin)
                            logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
                            loaded += 1
                            
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
        
        return loaded
    
    def _register_plugin(self, plugin: PluginBase):
        """Register plugin in appropriate category."""
        if isinstance(plugin, MetricsPlugin):
            self._metrics_plugins.append(plugin)
        if isinstance(plugin, AlertPlugin):
            self._alert_plugins.append(plugin)
        if isinstance(plugin, ExportPlugin):
            self._export_plugins.append(plugin)
    
    def collect_plugin_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all metrics plugins."""
        metrics = {}
        for plugin in self._metrics_plugins:
            try:
                plugin_metrics = plugin.collect_metrics()
                metrics[plugin.name] = plugin_metrics
            except Exception as e:
                logger.error(f"Plugin {plugin.name} metrics error: {e}")
        return metrics
    
    def check_plugin_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check alerts from all alert plugins."""
        alerts = []
        for plugin in self._alert_plugins:
            try:
                plugin_alerts = plugin.check_alerts(metrics)
                alerts.extend(plugin_alerts)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} alert error: {e}")
        return alerts
    
    def export_data(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """Export data via all export plugins."""
        results = {}
        for plugin in self._export_plugins:
            try:
                results[plugin.name] = plugin.export(data)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} export error: {e}")
                results[plugin.name] = False
        return results
    
    def unload_all(self):
        """Unload all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Plugin {plugin.name} cleanup error: {e}")
        self.plugins.clear()
        self._metrics_plugins.clear()
        self._alert_plugins.clear()
        self._export_plugins.clear()