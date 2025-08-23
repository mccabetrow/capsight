"""
Model Registry for CapSight ML Pipeline
Handles model versioning, loading, and metadata
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

from ..config import MODELS_PATH
from ..utils.seed import set_random_seed

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Central registry for managing ML model versions"""
    
    def __init__(self):
        self.models_path = MODELS_PATH
        self.models_path.mkdir(parents=True, exist_ok=True)
    
    def save_model(self, model_name: str, model_obj: Any, 
                   version: str = None, metadata: Dict = None) -> str:
        """Save model with versioning"""
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_dir = self.models_path / model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model object
        import joblib
        model_file = model_dir / "model.pkl"
        with open(model_file, 'wb') as f:
            joblib.dump(model_obj, f)
        
        # Save metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'model_name': model_name,
            'version': version,
            'saved_at': datetime.now().isoformat(),
            'model_file': str(model_file.relative_to(self.models_path))
        })
        
        metadata_file = model_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update latest symlink
        self._update_latest_link(model_name, version)
        
        logger.info(f"Model {model_name} version {version} saved to {model_dir}")
        
        return str(model_dir)
    
    def load_model(self, model_name: str, version: str = "latest") -> Tuple[Any, Dict]:
        """Load model and metadata"""
        
        if version == "latest":
            version = self._get_latest_version(model_name)
            if not version:
                raise FileNotFoundError(f"No models found for {model_name}")
        
        model_dir = self.models_path / model_name / version
        if not model_dir.exists():
            raise FileNotFoundError(f"Model {model_name} version {version} not found")
        
        # Load metadata
        metadata_file = model_dir / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        # Load model
        model_file = model_dir / "model.pkl"
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        import joblib
        with open(model_file, 'rb') as f:
            model_obj = joblib.load(f)
        
        logger.info(f"Loaded model {model_name} version {version}")
        
        return model_obj, metadata
    
    def list_models(self) -> Dict[str, List[str]]:
        """List all models and their versions"""
        
        models = {}
        
        for model_dir in self.models_path.iterdir():
            if model_dir.is_dir():
                model_name = model_dir.name
                versions = []
                
                for version_dir in model_dir.iterdir():
                    if version_dir.is_dir():
                        versions.append(version_dir.name)
                
                models[model_name] = sorted(versions, reverse=True)  # Newest first
        
        return models
    
    def list_versions(self, model_name: str) -> List[Dict[str, Any]]:
        """List versions for a specific model with metadata"""
        
        model_dir = self.models_path / model_name
        if not model_dir.exists():
            return []
        
        versions = []
        
        for version_dir in model_dir.iterdir():
            if version_dir.is_dir():
                version_info = {
                    'version': version_dir.name,
                    'path': str(version_dir)
                }
                
                # Load metadata if available
                metadata_file = version_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            version_info.update(metadata)
                    except:
                        pass
                
                versions.append(version_info)
        
        # Sort by version (newest first)
        versions.sort(key=lambda x: x['version'], reverse=True)
        
        return versions
    
    def get_model_info(self, model_name: str, version: str = "latest") -> Dict[str, Any]:
        """Get model information without loading the model"""
        
        if version == "latest":
            version = self._get_latest_version(model_name)
            if not version:
                raise FileNotFoundError(f"No models found for {model_name}")
        
        model_dir = self.models_path / model_name / version
        if not model_dir.exists():
            raise FileNotFoundError(f"Model {model_name} version {version} not found")
        
        info = {
            'model_name': model_name,
            'version': version,
            'path': str(model_dir)
        }
        
        # Load metadata
        metadata_file = model_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                info.update(metadata)
        
        # Add file info
        model_file = model_dir / "model.pkl"
        if model_file.exists():
            stat = model_file.stat()
            info['model_file_size'] = stat.st_size
            info['model_file_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return info
    
    def delete_model(self, model_name: str, version: str) -> bool:
        """Delete a specific model version"""
        
        if version == "latest":
            raise ValueError("Cannot delete 'latest' version, specify exact version")
        
        model_dir = self.models_path / model_name / version
        if not model_dir.exists():
            return False
        
        # Remove directory
        shutil.rmtree(model_dir)
        
        # Update latest link if this was the latest
        latest_version = self._get_latest_version(model_name)
        if latest_version:
            self._update_latest_link(model_name, latest_version)
        else:
            # Remove latest link if no versions left
            latest_link = self.models_path / model_name / "latest"
            if latest_link.exists():
                latest_link.unlink()
        
        logger.info(f"Deleted model {model_name} version {version}")
        
        return True
    
    def cleanup_old_versions(self, model_name: str, keep_versions: int = 5) -> int:
        """Keep only the N most recent versions of a model"""
        
        versions = self.list_versions(model_name)
        if len(versions) <= keep_versions:
            return 0
        
        # Delete old versions
        deleted_count = 0
        for version_info in versions[keep_versions:]:
            if self.delete_model(model_name, version_info['version']):
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old versions of {model_name}")
        
        return deleted_count
    
    def _get_latest_version(self, model_name: str) -> Optional[str]:
        """Get the latest version of a model"""
        
        model_dir = self.models_path / model_name
        if not model_dir.exists():
            return None
        
        versions = []
        for version_dir in model_dir.iterdir():
            if version_dir.is_dir() and version_dir.name != "latest":
                versions.append(version_dir.name)
        
        if not versions:
            return None
        
        # Sort versions and return the latest
        return sorted(versions)[-1]
    
    def _update_latest_link(self, model_name: str, version: str):
        """Update the 'latest' symlink for a model"""
        
        latest_link = self.models_path / model_name / "latest"
        target_dir = self.models_path / model_name / version
        
        # Remove existing link
        if latest_link.exists():
            latest_link.unlink()
        
        # Create new link (use junction on Windows)
        try:
            if os.name == 'nt':  # Windows
                # Use junction instead of symlink on Windows
                import subprocess
                subprocess.run([
                    'mklink', '/J', str(latest_link), str(target_dir)
                ], shell=True, check=True, capture_output=True)
            else:
                latest_link.symlink_to(target_dir)
        except Exception as e:
            logger.warning(f"Failed to create latest link for {model_name}: {e}")
    
    def export_model(self, model_name: str, version: str = "latest", 
                    export_path: str = None) -> str:
        """Export model to external location"""
        
        if version == "latest":
            version = self._get_latest_version(model_name)
        
        source_dir = self.models_path / model_name / version
        if not source_dir.exists():
            raise FileNotFoundError(f"Model {model_name} version {version} not found")
        
        if export_path is None:
            export_path = f"{model_name}_{version}.tar.gz"
        
        # Create archive
        import tarfile
        with tarfile.open(export_path, 'w:gz') as tar:
            tar.add(source_dir, arcname=f"{model_name}_{version}")
        
        logger.info(f"Exported model {model_name} version {version} to {export_path}")
        
        return export_path
    
    def import_model(self, archive_path: str) -> Tuple[str, str]:
        """Import model from external archive"""
        
        import tarfile
        
        # Extract to temporary location
        temp_dir = self.models_path / "temp_import"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # Find extracted directory
            extracted_dirs = list(temp_dir.iterdir())
            if len(extracted_dirs) != 1:
                raise ValueError("Archive should contain exactly one model directory")
            
            extracted_dir = extracted_dirs[0]
            
            # Parse model name and version
            dir_name = extracted_dir.name
            if '_' in dir_name:
                model_name, version = dir_name.rsplit('_', 1)
            else:
                model_name = dir_name
                version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Move to models directory
            target_dir = self.models_path / model_name / version
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(extracted_dir), str(target_dir))
            
            # Update latest link
            self._update_latest_link(model_name, version)
            
            logger.info(f"Imported model {model_name} version {version}")
            
            return model_name, version
            
        finally:
            # Cleanup temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get overall registry statistics"""
        
        models = self.list_models()
        total_models = len(models)
        total_versions = sum(len(versions) for versions in models.values())
        
        # Calculate total size
        total_size = 0
        for model_dir in self.models_path.rglob("*.pkl"):
            total_size += model_dir.stat().st_size
        
        return {
            'total_models': total_models,
            'total_versions': total_versions,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'models': models
        }

# Global registry instance
_registry = ModelRegistry()

def get_registry() -> ModelRegistry:
    """Get the global model registry instance"""
    return _registry

# Convenience functions
def save_model(model_name: str, model_obj: Any, version: str = None, metadata: Dict = None) -> str:
    """Save model using global registry"""
    return _registry.save_model(model_name, model_obj, version, metadata)

def load_latest(model_name: str) -> Tuple[Any, Dict]:
    """Load latest version of a model"""
    return _registry.load_model(model_name, "latest")

def list_all_models() -> Dict[str, List[str]]:
    """List all models in registry"""
    return _registry.list_models()

__all__ = [
    'ModelRegistry',
    'get_registry',
    'save_model',
    'load_latest', 
    'list_all_models'
]
