# SeekDB 基础文档

> **当前 MineKB 使用**: [pyseekdb](https://github.com/oceanbase/pyseekdb)（`pip install pyseekdb`）。嵌入式模式支持 Linux 与 macOS Apple Silicon（依赖 pylibseekdb v1.1.0+），Python 3.11+。

# 1. 产品目标

轻量版嵌入式产品形态以库的形式集成在用户应用程序中，为开发者提供更强大灵活的数据管理解决方案，让数据管理无处不在(微控制器、物联网设备、边缘计算、移动应用、数据中心)，快速上手使用ALL IN ONE(TP、AP、 AI Native)的产品能力

![img](https://intranetproxy.alipay.com/skylark/lark/0/2025/png/275819/1756967663128-f86fe123-fc82-4e95-a87f-40c7e887eb04.png)

# 2. 安装配置

## 2.1 MineKB 应用自动安装

MineKB 应用会在启动时**自动检查并安装** pyseekdb：在应用数据目录下创建 Python venv，并在 venv 中执行 `pip install pyseekdb`。

### 应用数据目录位置

默认（未设置 `CONFIG_DIR` 时）：

- **macOS**: `~/Library/Application Support/com.mine-kb.app/`
- **Linux**: `~/.local/share/com.mine-kb.app/`
- **Windows**: `%APPDATA%\com.mine-kb.app\`

pyseekdb 嵌入模式的数据目录为 **`{应用数据目录}/mine_kb.db/`**（子目录，不直接平铺在应用数据目录下）。配置、venv、tmp 等仍在应用数据目录根下。

**通过环境变量指定**：若设置环境变量 **`CONFIG_DIR`**，则以其值为应用数据根目录。本地开发时可在项目内使用固定目录，例如：

```bash
# 开发时默认（package.json 中 tauri:dev 已设置）
CONFIG_DIR=com.mine-kb

# 或自定义绝对/相对路径
CONFIG_DIR=/path/to/your/data
```

### 手动安装（可选）

若应用内自动安装失败，可在应用数据目录的 venv 中手动安装：

```bash
# 进入应用数据目录下的 venv
source "$CONFIG_DIR/venv/bin/activate"   # Linux/macOS
# 或 %CONFIG_DIR%\venv\Scripts\activate  # Windows

pip install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 验证安装

查看应用日志，应看到类似信息：

```
✅ pyseekdb 已安装
✅ Python 环境和 SeekDB 准备完成
✅ SeekDB 数据库连接正常
```

## 2.2 独立使用 SeekDB

如果要在其他 Python 项目中使用 SeekDB：

**方法一：通过 pip 安装（推荐，当前 MineKB 使用）**

```bash
pip install pyseekdb -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

用法请参阅 [pyseekdb 文档](https://github.com/oceanbase/pyseekdb)。嵌入式模式示例：

```python
from pyseekdb.client import SeekdbEmbeddedClient, AdminClient

client = SeekdbEmbeddedClient(path="/path/to/db_dir", database="mine_kb")
conn = client.get_raw_connection()
cursor = conn.cursor()
# ...
```

# 3. AI Native

向量检索、全文检索、混合检索等能力用法参见 [pyseekdb](https://github.com/oceanbase/pyseekdb) 文档。

# 4. 分析能力(OLAP)

数据导入、列存、物化视图、外表等用法参见 [pyseekdb](https://github.com/oceanbase/pyseekdb) 文档。

# 5. 事务能力(OLTP)

事务与自动提交等用法参见 [pyseekdb](https://github.com/oceanbase/pyseekdb) 文档。

# 6. 平滑切换至分布式版本

用户通过嵌入式版本快速验证好产品原型后，想切换至分布式版本使用集群分布式处理能力，只需要修改导入包和相关配置即可，主体应用逻辑保持不变

```bash
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=11002, user='root@sys', database='test')
```
