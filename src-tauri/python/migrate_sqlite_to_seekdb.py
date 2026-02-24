#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to SeekDB.
Uses pyseekdb (https://github.com/oceanbase/pyseekdb). Embedded mode: Linux and macOS Apple Silicon (pylibseekdb v1.1.0+).

Usage:
    python migrate_sqlite_to_seekdb.py <sqlite_db_path> <seekdb_path>

Example:
    python migrate_sqlite_to_seekdb.py mine_kb.db ./seekdb.db
"""

import sys
import os
import sqlite3
import json
import struct
from typing import List, Tuple, Any

try:
    from pyseekdb.client import SeekdbEmbeddedClient, AdminClient
except ImportError:
    print("Error: pyseekdb is required. Install with: pip install pyseekdb")
    sys.exit(1)

def read_blob_as_f64_array(blob_data: bytes) -> List[float]:
    """
    Convert binary blob (bincode serialized Vec<f64>) to list of floats
    This assumes the blob is a bincode-serialized Rust Vec<f64>
    """
    try:
        # bincode format for Vec<f64>: 8-byte length + array of f64s
        if len(blob_data) < 8:
            return []
        
        # Read length (u64, little-endian)
        length = struct.unpack('<Q', blob_data[:8])[0]
        
        # Read f64 values
        offset = 8
        values = []
        for _ in range(length):
            if offset + 8 > len(blob_data):
                break
            value = struct.unpack('<d', blob_data[offset:offset+8])[0]
            values.append(value)
            offset += 8
        
        return values
    except Exception as e:
        print(f"⚠️  Warning: Failed to parse embedding blob: {e}")
        return []

def _format_sql_value(value: Any) -> str:
    """Format a Python value for embedding in SQL (pylibseekdb uses single-arg execute)."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return "'" + str(value).replace("'", "''") + "'"


def migrate_table(sqlite_cursor, seekdb_cursor, table_name: str,
                  columns: List[str], transform_row=None):
    """
    Migrate a table from SQLite to SeekDB.

    Args:
        sqlite_cursor: SQLite cursor
        seekdb_cursor: SeekDB cursor (pylibseekdb: execute(sql) only)
        table_name: Name of the table
        columns: List of column names
        transform_row: Optional function to transform row data before insertion
    """
    print(f"📦 Migrating table: {table_name}")

    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = sqlite_cursor.fetchone()[0]
    print(f"   Found {total_rows} rows")

    if total_rows == 0:
        print(f"   ✓ Table {table_name} is empty, skipping")
        return

    column_str = ", ".join(columns)
    sqlite_cursor.execute(f"SELECT {column_str} FROM {table_name}")
    rows = sqlite_cursor.fetchall()

    migrated = 0
    failed = 0
    for row in rows:
        try:
            if transform_row:
                row = transform_row(row)
            values_str = ", ".join(_format_sql_value(v) for v in row)
            insert_sql = f"INSERT INTO {table_name} ({column_str}) VALUES ({values_str})"
            seekdb_cursor.execute(insert_sql)
            migrated += 1
            if migrated % 100 == 0:
                print(f"   Progress: {migrated}/{total_rows}")
        except Exception as e:
            print(f"   ⚠️  Failed to migrate row: {e}")
            failed += 1

    print(f"   ✓ Migrated {migrated} rows ({failed} failed)")

def migrate_sqlite_to_seekdb(sqlite_path: str, seekdb_path: str, db_name: str = "mine_kb"):
    """
    Main migration function
    """
    print("="*60)
    print("SQLite to SeekDB Migration")
    print("="*60)
    print(f"Source (SQLite): {sqlite_path}")
    print(f"Target (SeekDB): {seekdb_path}")
    print(f"Database name: {db_name}")
    print()
    
    # Connect to SQLite
    print("🔌 Connecting to SQLite database...")
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        print("   ✓ Connected to SQLite")
    except Exception as e:
        print(f"   ✗ Failed to connect to SQLite: {e}")
        return 1
    
    # Connect to SeekDB (pyseekdb embedded)
    print("🔌 Connecting to SeekDB (pyseekdb)...")
    try:
        if os.path.isfile(seekdb_path):
            seekdb_dir = os.path.abspath(os.path.dirname(seekdb_path))
        else:
            seekdb_dir = os.path.abspath(seekdb_path)
        admin = AdminClient(path=seekdb_dir)
        try:
            admin.create_database(db_name)
        except Exception as create_err:
            if "exist" not in str(create_err).lower() and "duplicate" not in str(create_err).lower():
                raise
        seekdb_client = SeekdbEmbeddedClient(path=seekdb_dir, database=db_name)
        seekdb_conn = seekdb_client.get_raw_connection()
        seekdb_cursor = seekdb_conn.cursor()
        print("   ✓ Connected to SeekDB")
    except Exception as e:
        print(f"   ✗ Failed to connect to SeekDB: {e}")
        sqlite_conn.close()
        return 1
    
    print()
    print("📋 Creating SeekDB schema...")
    
    # Create tables in SeekDB
    try:
        # Projects table
        seekdb_cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id VARCHAR(36) PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                document_count INTEGER DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        
        # Vector documents table
        seekdb_cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_documents (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL,
                document_id VARCHAR(36) NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536),
                metadata TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id, chunk_index)
            )
        """)
        
        # Create vector index
        try:
            seekdb_cursor.execute("""
                CREATE VECTOR INDEX idx_embedding ON vector_documents(embedding) 
                WITH (distance=l2, type=hnsw, lib=vsag)
            """)
        except:
            pass  # Index might already exist
        
        # Create regular indexes
        seekdb_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_id ON vector_documents(project_id)
        """)
        seekdb_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_id ON vector_documents(document_id)
        """)
        
        # Conversations table
        seekdb_cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL,
                title TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        
        # Messages table
        seekdb_cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id VARCHAR(36) PRIMARY KEY,
                conversation_id VARCHAR(36) NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                sources TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # Conversation indexes
        seekdb_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_project_id ON conversations(project_id)
        """)
        seekdb_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_conversation_id ON messages(conversation_id)
        """)
        
        seekdb_conn.commit()
        print("   ✓ Schema created")
    
    except Exception as e:
        print(f"   ✗ Failed to create schema: {e}")
        sqlite_conn.close()
        seekdb_client._cleanup()
        return 1
    
    print()
    print("📦 Starting data migration...")
    print()
    
    # Migrate projects
    migrate_table(
        sqlite_cursor, 
        seekdb_cursor,
        "projects",
        ["id", "name", "description", "status", "document_count", "created_at", "updated_at"]
    )
    
    print()
    
    # Migrate vector documents (with embedding conversion)
    def transform_vector_row(row):
        """Convert embedding BLOB to JSON array string"""
        id, project_id, document_id, chunk_index, content, embedding_blob, metadata, created_at = row
        
        # Parse embedding from binary blob
        embedding_list = read_blob_as_f64_array(embedding_blob)
        
        # Pad or truncate to 1536 dimensions
        if len(embedding_list) < 1536:
            # Pad with zeros
            embedding_list.extend([0.0] * (1536 - len(embedding_list)))
        elif len(embedding_list) > 1536:
            # Truncate
            embedding_list = embedding_list[:1536]
        
        # Convert to JSON array string
        embedding_str = "[" + ",".join(str(v) for v in embedding_list) + "]"
        
        return (id, project_id, document_id, chunk_index, content, 
                embedding_str, metadata, created_at)
    
    migrate_table(
        sqlite_cursor,
        seekdb_cursor,
        "vector_documents",
        ["id", "project_id", "document_id", "chunk_index", "content", 
         "embedding", "metadata", "created_at"],
        transform_row=transform_vector_row
    )
    
    print()
    
    # Migrate conversations
    migrate_table(
        sqlite_cursor,
        seekdb_cursor,
        "conversations",
        ["id", "project_id", "title", "created_at", "updated_at", "message_count"]
    )
    
    print()
    
    # Migrate messages
    migrate_table(
        sqlite_cursor,
        seekdb_cursor,
        "messages",
        ["id", "conversation_id", "role", "content", "created_at", "sources"]
    )
    
    print()
    print("💾 Committing changes...")
    try:
        seekdb_conn.commit()
        print("   ✓ Changes committed")
    except Exception as e:
        print(f"   ✗ Failed to commit: {e}")
        sqlite_conn.close()
        seekdb_client._cleanup()
        return 1

    # Close connections
    sqlite_conn.close()
    seekdb_client._cleanup()
    
    print()
    print("="*60)
    print("✅ Migration completed successfully!")
    print("="*60)
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python migrate_sqlite_to_seekdb.py <sqlite_db_path> <seekdb_path> [db_name]")
        print()
        print("Example:")
        print("  python migrate_sqlite_to_seekdb.py mine_kb.db ./seekdb.db")
        print("  python migrate_sqlite_to_seekdb.py mine_kb.db ./seekdb.db custom_db")
        sys.exit(1)
    
    sqlite_path = sys.argv[1]
    seekdb_path = sys.argv[2]
    db_name = sys.argv[3] if len(sys.argv) > 3 else "mine_kb"
    
    exit_code = migrate_sqlite_to_seekdb(sqlite_path, seekdb_path, db_name)
    sys.exit(exit_code)

