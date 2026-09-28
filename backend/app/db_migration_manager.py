"""Database migration manager - handles SOURCE_DB_URL changes and cleanup.

When the SOURCE_DB_URL environment variable changes, this manager:
1. Detects the change
2. Clears all Vanna vector databases (ChromaDB, FAISS)
3. Resets Vanna training metadata
4. Logs the migration for audit trail
"""
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatabaseChangeDetector:
    """Detects changes to SOURCE_DB_URL and manages cleanup."""
    
    # State file to track the last known database URL
    STATE_FILE = Path(__file__).parent.parent / ".db_state.txt"
    
    @classmethod
    def get_current_db_url(cls) -> str:
        """Get the current SOURCE_DB_URL from environment."""
        return os.getenv("SOURCE_DB_URL", "")
    
    @classmethod
    def get_previous_db_url(cls) -> Optional[str]:
        """Get the previously recorded SOURCE_DB_URL from state file."""
        try:
            if cls.STATE_FILE.exists():
                with open(cls.STATE_FILE, "r") as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not read previous DB URL from state file: {e}")
        return None
    
    @classmethod
    def save_current_db_url(cls, db_url: str) -> None:
        """Save the current SOURCE_DB_URL to state file."""
        try:
            with open(cls.STATE_FILE, "w") as f:
                f.write(db_url)
            logger.info(f"✅ Saved current database URL to state file")
        except Exception as e:
            logger.error(f"Failed to save database URL to state file: {e}")
    
    @classmethod
    def has_db_changed(cls) -> bool:
        """Check if SOURCE_DB_URL has changed since last startup."""
        current = cls.get_current_db_url()
        previous = cls.get_previous_db_url()
        
        if not current:
            logger.warning("⚠️  SOURCE_DB_URL not set in environment")
            return False
        
        if previous is None:
            logger.info("📝 First startup - no previous database URL to compare")
            return False
        
        # Normalize URLs for comparison (remove trailing slashes, standardize case)
        current_normalized = current.rstrip('/').lower()
        previous_normalized = previous.rstrip('/').lower()
        
        if current_normalized != previous_normalized:
            logger.warning(f"🔄 DATABASE CHANGE DETECTED!")
            logger.warning(f"   Previous: {previous}")
            logger.warning(f"   Current:  {current}")
            return True
        
        return False


class VannaVectorStoreCleanup:
    """Handles cleanup of Vanna vector store files and metadata."""
    
    @staticmethod
    def get_vector_store_paths() -> Dict[str, Path]:
        """Get paths to all vector store directories."""
        project_root = Path(__file__).parent.parent.parent
        
        return {
            "chromadb": project_root / os.getenv("CHROMA_PATH", "./vanna_chroma"),
            "faiss": project_root / os.getenv("FAISS_PATH", "./vanna_faiss"),
        }
    
    @classmethod
    def cleanup_vector_stores(cls) -> Dict[str, bool]:
        """Remove all vector store directories."""
        results = {}
        paths = cls.get_vector_store_paths()
        
        for store_name, store_path in paths.items():
            try:
                if store_path.exists():
                    shutil.rmtree(store_path)
                    logger.info(f"🗑️  Deleted {store_name} vector store: {store_path}")
                    results[store_name] = True
                else:
                    logger.debug(f"ℹ️  {store_name} vector store not found: {store_path}")
                    results[store_name] = False
            except Exception as e:
                logger.error(f"❌ Failed to delete {store_name} vector store: {e}")
                results[store_name] = False
        
        return results
    
    @classmethod
    def cleanup_pycache(cls) -> bool:
        """Remove Python cache files to force reimports."""
        try:
            project_root = Path(__file__).parent.parent.parent
            backend_path = project_root / "backend"
            
            count = 0
            for pycache in backend_path.rglob("__pycache__"):
                if pycache.exists():
                    shutil.rmtree(pycache)
                    count += 1
            
            if count > 0:
                logger.info(f"🗑️  Deleted {count} __pycache__ directories")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clean Python cache: {e}")
            return False


class VannaTrainingDataReset:
    """Resets Vanna training metadata in the admin database."""
    
    @staticmethod
    def reset_training_data(db_session) -> Dict[str, Any]:
        """Clear all Vanna training data from the admin database.
        
        This includes:
        - training_items (DDL, documentation, sample Q&A)
        - vanna_ddl (cached DDL from training)
        - Any Vanna-specific metadata
        
        Args:
            db_session: SQLAlchemy session to admin database
            
        Returns:
            Dict with cleanup results
        """
        results = {
            "training_items_cleared": False,
            "vanna_metadata_cleared": False,
            "error": None
        }
        
        try:
            # Check if training_items table exists and clear it
            from sqlalchemy import text, inspect
            inspector = inspect(db_session.bind)
            tables = inspector.get_table_names()
            
            if "training_items" in tables:
                db_session.execute(text("DELETE FROM training_items"))
                db_session.commit()
                logger.info("🗑️  Cleared training_items table")
                results["training_items_cleared"] = True
            
            # Clear any other Vanna-related metadata tables
            vanna_tables = [t for t in tables if 'vanna' in t.lower() or 'training' in t.lower()]
            for table_name in vanna_tables:
                if table_name != "training_items":  # Already handled
                    try:
                        db_session.execute(text(f"DELETE FROM {table_name}"))
                        logger.info(f"🗑️  Cleared {table_name}")
                        results["vanna_metadata_cleared"] = True
                    except Exception as e:
                        logger.warning(f"Could not clear {table_name}: {e}")
            
            db_session.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to reset training data: {e}")
            results["error"] = str(e)
        
        return results


class DatabaseMigrationOrchestrator:
    """Orchestrates the full database migration cleanup process."""
    
    @staticmethod
    def migrate_database(db_session) -> Dict[str, Any]:
        """Execute full database migration cleanup if needed.
        
        Args:
            db_session: SQLAlchemy session to admin database
            
        Returns:
            Dict with migration status and details
        """
        current_db = DatabaseChangeDetector.get_current_db_url()
        previous_db = DatabaseChangeDetector.get_previous_db_url()
        
        result = {
            "migration_needed": False,
            "previous_db": previous_db,
            "current_db": current_db,
            "steps_completed": [],
            "errors": []
        }
        
        # Check if migration is needed
        if not DatabaseChangeDetector.has_db_changed():
            logger.info("✅ No database change detected - skipping migration")
            return result
        
        result["migration_needed"] = True
        logger.warning("⚠️  DATABASE MIGRATION STARTING - Cleaning old database artifacts...")
        
        try:
            # Step 1: Clean vector stores
            logger.info("\n📦 Step 1: Cleaning vector stores...")
            vector_cleanup = VannaVectorStoreCleanup.cleanup_vector_stores()
            result["steps_completed"].append(("vector_store_cleanup", vector_cleanup))
            
            # Step 2: Clean Python cache
            logger.info("\n🧹 Step 2: Cleaning Python cache...")
            cache_cleanup = VannaVectorStoreCleanup.cleanup_pycache()
            result["steps_completed"].append(("pycache_cleanup", cache_cleanup))
            
            # Step 3: Reset training data in admin DB
            logger.info("\n🗑️  Step 3: Resetting Vanna training data...")
            training_reset = VannaTrainingDataReset.reset_training_data(db_session)
            result["steps_completed"].append(("training_data_reset", training_reset))
            
            # Step 4: Update state file
            logger.info("\n💾 Step 4: Updating state file...")
            DatabaseChangeDetector.save_current_db_url(current_db)
            result["steps_completed"].append(("state_file_updated", True))
            
            logger.warning("\n" + "=" * 70)
            logger.warning("✅ DATABASE MIGRATION COMPLETED")
            logger.warning(f"   Old database: {previous_db}")
            logger.warning(f"   New database: {current_db}")
            logger.warning("   ➜ All old training data and vector stores have been cleared")
            logger.warning("   ➜ Vanna will be retrained on the new database on next startup")
            logger.warning("=" * 70 + "\n")
            
        except Exception as e:
            logger.error(f"❌ Migration failed with error: {e}")
            result["errors"].append(str(e))
        
        return result


def initialize_database_migration(app, db_session):
    """Call this during app startup to handle database migrations.
    
    Args:
        app: Flask application instance
        db_session: SQLAlchemy session to admin database
    """
    logger.info("\n" + "=" * 70)
    logger.info("🔍 CHECKING FOR DATABASE CHANGES...")
    logger.info("=" * 70)
    
    try:
        result = DatabaseMigrationOrchestrator.migrate_database(db_session)
        
        if result["migration_needed"]:
            logger.warning("\n⚠️  IMPORTANT: Restart your backend service for Vanna to retrain")
            logger.warning("              on the new database schema.")
        else:
            logger.info("✅ Database unchanged - continuing with normal startup")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Database migration check failed: {e}")
        logger.warning("⚠️  Continuing with startup (manual cleanup may be needed)")
        return {"error": str(e)}
