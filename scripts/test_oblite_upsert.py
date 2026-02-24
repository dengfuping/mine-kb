#!/usr/bin/env python3
"""
测试 SeekDB（pyseekdb）的 UPSERT 语法支持
使用 pyseekdb，与 MineKB 应用一致。
"""
import sys
import os
import tempfile
import shutil

# 添加 src-tauri/python 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src-tauri', 'python'))

try:
    from pyseekdb.client import SeekdbEmbeddedClient, AdminClient
    print("✅ pyseekdb 模块加载成功")
except ImportError as e:
    print(f"❌ 无法导入 pyseekdb: {e}")
    print("  请安装: pip install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple/")
    sys.exit(1)


def test_upsert_syntax():
    """测试不同的 UPSERT 语法"""
    test_dir = tempfile.mkdtemp(prefix="test_seekdb_upsert_")
    test_db_name = "test_upsert"

    print(f"\n📋 测试 SeekDB (pyseekdb) UPSERT 语法")
    print(f"数据库目录: {test_dir}")
    print(f"数据库名: {test_db_name}")

    try:
        # 创建数据库（如需要）
        admin = AdminClient(path=test_dir)
        try:
            admin.create_database(test_db_name)
        except Exception as e:
            if "exist" not in str(e).lower() and "duplicate" not in str(e).lower():
                raise

        client = SeekdbEmbeddedClient(path=test_dir, database=test_db_name)
        conn = client.get_raw_connection()
        cursor = conn.cursor()
        print(f"✅ 已连接到数据库 '{test_db_name}'")

        # 创建测试表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_projects (
                id VARCHAR(36) PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        print("✅ 测试表创建成功")

        # 测试 1: 基本 INSERT
        print("\n📝 测试 1: 基本 INSERT")
        cursor.execute("INSERT INTO test_projects VALUES ('test-1', 'Project 1', 10)")
        conn.commit()
        cursor.execute("SELECT * FROM test_projects WHERE id = 'test-1'")
        result = cursor.fetchone()
        print(f"   结果: {result}")

        # 测试 2: REPLACE INTO (MySQL 风格)
        print("\n📝 测试 2: REPLACE INTO")
        try:
            cursor.execute("REPLACE INTO test_projects VALUES ('test-1', 'Project 1 Updated', 20)")
            conn.commit()
            cursor.execute("SELECT * FROM test_projects WHERE id = 'test-1'")
            result = cursor.fetchone()
            print(f"   ✅ REPLACE INTO 语法支持！")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"   ❌ REPLACE INTO 不支持: {e}")

        # 测试 3: ON DUPLICATE KEY UPDATE (MySQL 风格)
        print("\n📝 测试 3: ON DUPLICATE KEY UPDATE")
        try:
            cursor.execute("""
                INSERT INTO test_projects VALUES ('test-2', 'Project 2', 30)
                ON DUPLICATE KEY UPDATE name = 'Project 2 Updated', value = 40
            """)
            conn.commit()
            cursor.execute("SELECT * FROM test_projects WHERE id = 'test-2'")
            result = cursor.fetchone()
            print(f"   ✅ ON DUPLICATE KEY UPDATE 语法支持！")
            print(f"   结果: {result}")

            cursor.execute("""
                INSERT INTO test_projects VALUES ('test-2', 'Project 2 Updated Again', 50)
                ON DUPLICATE KEY UPDATE name = 'Project 2 Updated Again', value = 50
            """)
            conn.commit()
            cursor.execute("SELECT * FROM test_projects WHERE id = 'test-2'")
            result = cursor.fetchone()
            print(f"   结果（更新后）: {result}")
        except Exception as e:
            print(f"   ❌ ON DUPLICATE KEY UPDATE 不支持: {e}")

        # 测试 4: ON CONFLICT DO UPDATE (SQLite 风格)
        print("\n📝 测试 4: ON CONFLICT DO UPDATE")
        try:
            cursor.execute("""
                INSERT INTO test_projects VALUES ('test-3', 'Project 3', 60)
                ON CONFLICT(id) DO UPDATE SET name = 'Project 3 Updated', value = 70
            """)
            conn.commit()
            cursor.execute("SELECT * FROM test_projects WHERE id = 'test-3'")
            result = cursor.fetchone()
            print(f"   ✅ ON CONFLICT DO UPDATE 语法支持！")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"   ❌ ON CONFLICT DO UPDATE 不支持: {e}")

        # 测试 5: INSERT ... ON CONFLICT DO UPDATE with excluded
        print("\n📝 测试 5: INSERT ... ON CONFLICT DO UPDATE with excluded")
        try:
            cursor.execute("""
                INSERT INTO test_projects (id, name, value)
                VALUES ('test-4', 'Project 4', 80)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    value = excluded.value
            """)
            conn.commit()
            cursor.execute("SELECT * FROM test_projects WHERE id = 'test-4'")
            result = cursor.fetchone()
            print(f"   ✅ ON CONFLICT DO UPDATE with excluded 语法支持！")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"   ❌ ON CONFLICT DO UPDATE with excluded 不支持: {e}")

        print("\n📊 最终数据:")
        cursor.execute("SELECT * FROM test_projects ORDER BY id")
        for row in cursor.fetchall():
            print(f"   {row}")

        client._cleanup()
        print("\n✅ 测试完成")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    return True


if __name__ == "__main__":
    success = test_upsert_syntax()
    sys.exit(0 if success else 1)
