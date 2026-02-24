# SeekDB Setup Checklist

Follow these steps to set up the application with pyseekdb (SeekDB) support.

## Prerequisites

**构建/开发环境**（仅开发或打包时需要）：

- [ ] Python 3.11+ installed（应用首次运行时会用其创建 venv 并安装 pyseekdb）
  ```bash
  python3 --version
  ```

- [ ] pip3 / python3-venv（Linux 需 `sudo apt install python3-venv`）
  ```bash
  pip3 --version
  python3 -m venv --help
  ```

- [ ] Rust 1.70+ installed (for building)
  ```bash
  rustc --version
  ```

- [ ] Node.js 16+ installed (for frontend build)
  ```bash
  node --version
  ```

**安装后运行环境**：用户机器仅需已安装 **Python 3**（建议 3.11+）。Node.js 和 Rust 不需要。

## Installation Steps

### 1. Install pyseekdb（可选，应用会自动安装）

应用首次运行会在应用数据目录下创建 venv 并安装 pyseekdb。若需提前验证环境：

```bash
# Using pip with Tsinghua mirror (recommended in China)
pip3 install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Or using the installation script
cd src-tauri/python
bash install_deps.sh
```

### 2. Verify Installation

```bash
cd src-tauri/python
python3 test_seekdb.py
```

Expected output:
```
============================================================
pyseekdb Installation Test
============================================================
Testing pyseekdb import... ✅ OK
...
✅ All tests passed! SeekDB is ready to use.
============================================================
```

### 3. Install Application Dependencies

```bash
# From project root
cd /home/ubuntu/Desktop/mine-kb

# Install frontend dependencies
npm install  # or tnpm install

# Rust dependencies will be installed automatically during build
```

### 4. Configure Application

```bash
# Copy config template
cp src-tauri/config.example.json src-tauri/config.json

# Edit config file and add your API keys
nano src-tauri/config.json
```

### 5. Build and Run

```bash
# Development mode（默认数据目录为 src-tauri/com.mine-kb，由 CONFIG_DIR=com.mine-kb 指定）
npm run tauri:dev

# 自定义数据目录
CONFIG_DIR=/path/to/your/data npm run tauri:dev

# Production build
npm run tauri:build
```

## Migration from SQLite (If Upgrading)

If you have an existing SQLite database:

```bash
cd src-tauri/python
python3 migrate_sqlite_to_seekdb.py <old_sqlite_path> <seekdb_path>
```

Example:
```bash
# macOS
python3 migrate_sqlite_to_seekdb.py ~/Library/Application\ Support/com.mine-kb.app/mine_kb.db ./seekdb.db

# Linux
python3 migrate_sqlite_to_seekdb.py ~/.local/share/com.mine-kb.app/mine_kb.db ./seekdb.db

# Windows
python3 migrate_sqlite_to_seekdb.py %APPDATA%\com.mine-kb.app\mine_kb.db .\seekdb.db
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pyseekdb'"

**Solution:** 应用会在数据目录 venv 中自动安装；若失败可手动安装：
```bash
# 进入应用数据目录的 venv 后
pip3 install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### Issue: "Failed to start Python process"

**Solutions:**
1. Verify Python 3 is in PATH:
   ```bash
   which python3
   ```

2. Check if pyseekdb is installed (in app venv or system):
   ```bash
   python3 -c "import pyseekdb; print('OK')"
   ```

3. Check script permissions:
   ```bash
   chmod +x src-tauri/python/seekdb_bridge.py
   ```

### Issue: "Vector index creation failed"

This is usually not critical. The application will work without the index, just slower for large datasets.

To manually create index later:
```sql
CREATE VECTOR INDEX idx_embedding ON vector_documents(embedding) 
WITH (distance=l2, type=hnsw, lib=vsag)
```

### Issue: Subprocess communication timeout

**Solutions:**
1. Restart the application
2. Check system resources (CPU/memory)
3. Check Python process logs in stderr

## Verification

After setup, verify everything works:

1. [ ] Application starts without errors
2. [ ] Can create a new project
3. [ ] Can upload a document
4. [ ] Document processing completes
5. [ ] Can query the document via chat
6. [ ] Chat responses are generated correctly
7. [ ] Data persists after application restart

## Getting Help

- Check [docs/seekdb.md](docs/seekdb.md) for SeekDB/pyseekdb documentation
- Create an issue on GitHub

## Checklist Summary

- [ ] Python 3.11+ installed（运行环境必需；构建时亦需要 Node.js、Rust）
- [ ] pyseekdb 可由应用自动安装或已手动安装
- [ ] Installation test passed（可选：运行 `src-tauri/python/test_seekdb.py`）
- [ ] Application dependencies installed（npm install）
- [ ] Configuration file created（如 `src-tauri/config.json` 或应用数据目录下 config.json）
- [ ] Application builds successfully
- [ ] Application runs without errors
- [ ] (If upgrading) Data migrated from SQLite

Once all items are checked, you're ready to use MineKB with SeekDB! 🎉

