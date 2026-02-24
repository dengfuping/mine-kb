#!/usr/bin/env python3
"""
Simple test script to verify pyseekdb installation and basic operations.
Embedded mode (SeekdbEmbeddedClient) uses pylibseekdb (Linux + macOS Apple Silicon v1.1.0+).
"""

import sys
import os

def test_import():
    """Test if pyseekdb module can be imported"""
    print("Testing pyseekdb import...", end=" ")
    try:
        import pyseekdb
        print("✅ OK")
        return True
    except ImportError as e:
        print(f"❌ FAILED: {e}")
        print("\nPlease install pyseekdb:")
        print("  pip install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple/")
        return False

def _embedded_available():
    """Check if embedded client (pylibseekdb) is available (Linux or macOS Apple Silicon)."""
    try:
        from pyseekdb.client.client_seekdb_embedded import _PYLIBSEEKDB_AVAILABLE
        return _PYLIBSEEKDB_AVAILABLE
    except ImportError:
        return False

def test_basic_operations():
    """Test basic database operations (embedded mode)."""
    print("\nTesting basic operations (embedded)...")
    if not _embedded_available():
        print("  ⏭ Skipped: embedded mode requires pylibseekdb (Linux or macOS Apple Silicon)")
        return True

    try:
        from pyseekdb.client import SeekdbEmbeddedClient, AdminClient
        import tempfile

        temp_dir = tempfile.mkdtemp()
        db_dir = temp_dir

        print(f"  Creating database at {db_dir}...", end=" ")
        admin = AdminClient(path=db_dir)
        admin.create_database("test_db")
        client = SeekdbEmbeddedClient(path=db_dir, database="test_db")
        conn = client.get_raw_connection()
        cursor = conn.cursor()
        print("✅")
        
        # Create table
        print("  Creating table...", end=" ")
        cursor.execute("CREATE TABLE test_table (id INT PRIMARY KEY, name VARCHAR(50))")
        print("✅")
        
        # Insert data
        print("  Inserting data...", end=" ")
        cursor.execute("INSERT INTO test_table VALUES (1, 'Test')")
        conn.commit()
        print("✅")
        
        # Query data
        print("  Querying data...", end=" ")
        cursor.execute("SELECT * FROM test_table")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == 'Test'
        print("✅")
        
        # Close connection
        print("  Closing connection...", end=" ")
        client._cleanup()
        print("✅")

        import shutil
        shutil.rmtree(temp_dir)
        
        print("\n✅ All basic operations passed!")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_operations():
    """Test vector operations (embedded mode)."""
    print("\nTesting vector operations...")
    if not _embedded_available():
        print("  ⏭ Skipped: embedded mode requires pylibseekdb (Linux or macOS Apple Silicon)")
        return True

    try:
        from pyseekdb.client import SeekdbEmbeddedClient, AdminClient
        import tempfile

        temp_dir = tempfile.mkdtemp()
        admin = AdminClient(path=temp_dir)
        admin.create_database("test_vector")
        client = SeekdbEmbeddedClient(path=temp_dir, database="test_vector")
        conn = client.get_raw_connection()
        cursor = conn.cursor()
        print("  Creating vector database...", end=" ")
        print("✅")
        
        # Create table with vector column
        print("  Creating table with vector column...", end=" ")
        cursor.execute("""
            CREATE TABLE test_vectors (
                id INT PRIMARY KEY,
                embedding vector(3)
            )
        """)
        print("✅")
        
        # Create vector index
        print("  Creating vector index...", end=" ")
        try:
            cursor.execute("""
                CREATE VECTOR INDEX idx_test ON test_vectors(embedding) 
                WITH (distance=l2, type=hnsw, lib=vsag)
            """)
            print("✅")
        except Exception as e:
            print(f"⚠️  SKIPPED: {e}")
        
        # Insert vector data
        print("  Inserting vector data...", end=" ")
        cursor.execute("INSERT INTO test_vectors VALUES (1, '[1.0, 2.0, 3.0]')")
        cursor.execute("INSERT INTO test_vectors VALUES (2, '[2.0, 3.0, 4.0]')")
        conn.commit()
        print("✅")
        
        # Vector similarity search
        print("  Testing vector search...", end=" ")
        cursor.execute("""
            SELECT id, l2_distance(embedding, '[1.0, 2.0, 3.0]') as distance
            FROM test_vectors
            ORDER BY distance
            LIMIT 1
        """)
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1  # Should return the exact match
        print("✅")
        
        client._cleanup()
        import shutil
        shutil.rmtree(temp_dir)

        print("\n✅ All vector operations passed!")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("pyseekdb Installation Test")
    print("="*60)
    
    # Test import
    if not test_import():
        sys.exit(1)
    
    # Test basic operations
    if not test_basic_operations():
        sys.exit(1)
    
    # Test vector operations
    if not test_vector_operations():
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ All tests passed! SeekDB is ready to use.")
    print("="*60)
    sys.exit(0)

if __name__ == "__main__":
    main()

