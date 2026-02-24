#!/usr/bin/env python3
"""
SeekDB Bridge - Python subprocess that handles database operations via JSON protocol.
Uses pyseekdb (https://github.com/oceanbase/pyseekdb). Embedded mode: Linux and macOS Apple Silicon (pylibseekdb v1.1.0+).
Communicates with Rust via stdin/stdout using newline-delimited JSON.
"""

import sys
import json
import traceback
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal

# Use pyseekdb; embedded mode uses SeekdbEmbeddedClient (pylibseekdb; Linux + macOS Apple Silicon)
try:
    import pyseekdb
    from pyseekdb.client import SeekdbEmbeddedClient, AdminClient
except ImportError as e:
    print(f"[SeekDB Bridge] ❌ 无法导入 pyseekdb 模块", file=sys.stderr)
    print(f"[SeekDB Bridge] 错误详情: {e}", file=sys.stderr)
    print(f"[SeekDB Bridge] 诊断信息: Python={sys.version}, executable={sys.executable}", file=sys.stderr)
    print(f"[SeekDB Bridge] 请安装: python -m pip install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"[SeekDB Bridge] ❌ 加载 pyseekdb 时发生错误: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

class SeekDBBridge:
    def __init__(self):
        self._client = None  # SeekdbEmbeddedClient, keep ref so connection lives
        self.conn = None
        self.cursor = None
        self.db_path = None
        self.db_name = None
        self.db_dir = None  # directory path for pyseekdb
        
    def log(self, msg: str):
        """Log to stderr (stdout is reserved for responses)"""
        print(f"[SeekDB Bridge] {msg}", file=sys.stderr, flush=True)
    
    def convert_value_for_json(self, value: Any) -> Any:
        """Convert Python objects to JSON-serializable format"""
        if value is None:
            return None
        elif isinstance(value, (datetime, date)):
            # Convert datetime/date to ISO format string
            return value.isoformat()
        elif isinstance(value, Decimal):
            # Convert Decimal to float
            return float(value)
        elif isinstance(value, bytes):
            # Convert bytes to base64 string
            import base64
            return base64.b64encode(value).decode('utf-8')
        elif isinstance(value, (list, tuple)):
            # Recursively convert list/tuple items
            return [self.convert_value_for_json(v) for v in value]
        elif isinstance(value, dict):
            # Recursively convert dict values
            return {k: self.convert_value_for_json(v) for k, v in value.items()}
        else:
            # Return as-is for basic types (str, int, float, bool)
            return value
    
    def format_sql_value(self, value: Any) -> str:
        """Format a Python value to SQL string representation for ObLite"""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape single quotes in strings
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, list):
            # For vector/array values
            return str(value)
        else:
            # For other types, convert to string and quote
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
    
    def _find_placeholder_pos(self, sql: str) -> int:
        """Find position of the first ? that is not inside a single-quoted string (SQL '' = escaped quote)."""
        i = 0
        in_string = False
        n = len(sql)
        while i < n:
            if sql[i] == "'":
                if in_string and i + 1 < n and sql[i + 1] == "'":
                    i += 2  # skip escaped ''
                    continue
                in_string = not in_string
                i += 1
                continue
            if not in_string and sql[i] == "?":
                return i
            i += 1
        return -1

    def build_sql_with_values(self, sql: str, values: List[Any]) -> str:
        """
        Replace ? placeholders in SQL with actual values.
        Only replaces ? that are not inside single-quoted strings, so content/embedding
        containing ? or ' do not break substitution.
        """
        if not values:
            return sql
        
        result = sql
        for value in values:
            pos = self._find_placeholder_pos(result)
            if pos < 0:
                break
            formatted_value = self.format_sql_value(value)
            result = result[:pos] + formatted_value + result[pos + 1:]
        
        return result
    
    def send_response(self, response: Dict[str, Any]):
        """Send JSON response to stdout"""
        json.dump(response, sys.stdout)
        sys.stdout.write('\n')
        sys.stdout.flush()
    
    def send_success(self, data: Any = None):
        """Send success response"""
        self.send_response({"status": "success", "data": data})
    
    def send_error(self, error: str, details: str = ""):
        """Send error response"""
        self.send_response({
            "status": "error",
            "error": error,
            "details": details
        })
    
    def handle_init(self, params: Dict[str, Any]):
        """Initialize SeekDB connection via pyseekdb (embedded mode)."""
        try:
            db_path = params.get("db_path", "./seekdb.db")
            db_name = params.get("db_name", "mine_kb")

            # 嵌入模式数据目录：固定为 path 所表示的目录（如 .../com.mine-kb.app/mine_kb.db），不平铺到父目录
            db_dir = os.path.abspath(db_path)
            if os.path.isfile(db_dir):
                self.log(f"WARNING: path exists as file, renaming to {db_dir}.old")
                try:
                    os.rename(db_dir, db_dir + ".old")
                except OSError:
                    pass
            if not os.path.isdir(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            self.log(f"Initializing pyseekdb: path={db_path}, db_dir={db_dir}, db={db_name}")

            try:
                # Create database if not exists (AdminClient for embedded path)
                admin = AdminClient(path=db_dir)
                try:
                    admin.create_database(db_name)
                    self.log(f"✅ Database '{db_name}' created")
                except Exception as create_err:
                    if "exist" not in str(create_err).lower() and "duplicate" not in str(create_err).lower():
                        raise Exception(f"Cannot create database '{db_name}': {create_err}")
                    self.log(f"Database '{db_name}' already exists")
            except RuntimeError as re:
                if "pylibseekdb" in str(re) or "not available" in str(re):
                    self.log("Embedded mode requires pylibseekdb (Linux or macOS Apple Silicon v1.1.0+). Install pyseekdb which pulls pylibseekdb.")
                raise

            # Connect using embedded client and get raw connection for SQL
            self._client = SeekdbEmbeddedClient(path=db_dir, database=db_name)
            self.conn = self._client.get_raw_connection()
            self.cursor = self.conn.cursor()
            self.db_path = db_path
            self.db_name = db_name
            self.db_dir = db_dir

            self.log("pyseekdb initialized successfully")
            self.send_success({"db_path": db_path, "db_name": db_name})

        except Exception as e:
            self.log(f"Init error: {e}")
            self.log(f"Traceback: {traceback.format_exc()}")
            error_details = (
                f"数据库初始化失败\n"
                f"路径: {params.get('db_path', './seekdb.db')}\n"
                f"数据库名: {params.get('db_name', 'mine_kb')}\n"
                f"错误: {str(e)}\n"
                f"说明: 嵌入式模式需 pylibseekdb（Linux 或 macOS Apple Silicon v1.1.0+）"
            )
            self.send_error("InitError", error_details)
    
    def handle_execute(self, params: Dict[str, Any]):
        """Execute SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.)"""
        try:
            sql = params["sql"]
            values = params.get("values", [])
            
            # ObLite doesn't support parameterized queries, embed values directly
            final_sql = self.build_sql_with_values(sql, values)
            
            self.log(f"Executing: {final_sql[:200]}...")
            
            # ObLite execute() only accepts one argument
            self.cursor.execute(final_sql)
            
            rows_affected = self.cursor.rowcount if hasattr(self.cursor, 'rowcount') else 0
            self.send_success({"rows_affected": rows_affected})
            
        except Exception as e:
            self.log(f"Execute error: {e}")
            self.send_error("ExecuteError", str(e))
    
    def handle_query(self, params: Dict[str, Any]):
        """Execute SELECT query and return results"""
        try:
            sql = params["sql"]
            values = params.get("values", [])
            
            # ObLite doesn't support parameterized queries, embed values directly
            final_sql = self.build_sql_with_values(sql, values)
            
            self.log(f"Querying: {final_sql[:200]}...")
            
            # ObLite execute() only accepts one argument
            self.cursor.execute(final_sql)
            
            rows = self.cursor.fetchall()
            
            # Convert rows to list of lists, handling datetime and other special types
            if rows:
                result = []
                for row in rows:
                    converted_row = [self.convert_value_for_json(val) for val in row]
                    result.append(converted_row)
            else:
                result = []
            
            self.log(f"Query returned {len(result)} rows")
            self.send_success({"rows": result})
            
        except Exception as e:
            self.log(f"Query error: {e}")
            self.log(f"Traceback: {traceback.format_exc()}")
            self.send_error("QueryError", str(e))
    
    def handle_query_one(self, params: Dict[str, Any]):
        """Execute SELECT query and return first row"""
        try:
            sql = params["sql"]
            values = params.get("values", [])
            
            # ObLite doesn't support parameterized queries, embed values directly
            final_sql = self.build_sql_with_values(sql, values)
            
            # ObLite execute() only accepts one argument
            self.cursor.execute(final_sql)
            
            row = self.cursor.fetchone()
            
            # Convert row values, handling datetime and other special types
            if row:
                result = [self.convert_value_for_json(val) for val in row]
            else:
                result = None
            
            self.send_success({"row": result})
            
        except Exception as e:
            self.log(f"Query one error: {e}")
            self.log(f"Traceback: {traceback.format_exc()}")
            self.send_error("QueryOneError", str(e))
    
    def handle_commit(self, params: Dict[str, Any]):
        """Commit current transaction"""
        try:
            self.log("Committing transaction")
            self.conn.commit()
            self.send_success()
            
        except Exception as e:
            self.log(f"Commit error: {e}")
            self.send_error("CommitError", str(e))
    
    def handle_rollback(self, params: Dict[str, Any]):
        """Rollback current transaction"""
        try:
            self.log("Rolling back transaction")
            self.conn.rollback()
            self.send_success()
            
        except Exception as e:
            self.log(f"Rollback error: {e}")
            self.send_error("RollbackError", str(e))
    
    def handle_ping(self, params: Dict[str, Any]):
        """Health check"""
        self.send_success({"message": "pong"})
    
    def handle_command(self, command: Dict[str, Any]):
        """Route command to appropriate handler"""
        cmd_type = command.get("command")
        params = command.get("params", {})
        
        handlers = {
            "init": self.handle_init,
            "execute": self.handle_execute,
            "query": self.handle_query,
            "query_one": self.handle_query_one,
            "commit": self.handle_commit,
            "rollback": self.handle_rollback,
            "ping": self.handle_ping,
        }
        
        handler = handlers.get(cmd_type)
        if handler:
            handler(params)
        else:
            self.send_error("UnknownCommand", f"Unknown command: {cmd_type}")
    
    def run(self):
        """Main loop - read commands from stdin and execute them"""
        self.log("SeekDB Bridge started, waiting for commands...")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    command = json.loads(line)
                    self.handle_command(command)
                    
                except json.JSONDecodeError as e:
                    self.log(f"JSON decode error: {e}")
                    self.send_error("JSONError", str(e))
                    
                except Exception as e:
                    self.log(f"Unexpected error: {e}")
                    self.log(traceback.format_exc())
                    self.send_error("InternalError", str(e))
        
        except KeyboardInterrupt:
            self.log("Received interrupt signal, shutting down...")
        
        finally:
            if self._client is not None:
                try:
                    self._client._cleanup()
                    self.log("Database connection closed")
                except Exception:
                    pass
            elif self.conn is not None:
                try:
                    self.conn.close()
                    self.log("Database connection closed")
                except Exception:
                    pass

if __name__ == "__main__":
    bridge = SeekDBBridge()
    bridge.run()

