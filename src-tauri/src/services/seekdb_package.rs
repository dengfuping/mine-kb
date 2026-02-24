use anyhow::{anyhow, Result};
use std::process::Command;
use super::python_env::PythonEnv;

const PYSEEKDB_PACKAGE: &str = "pyseekdb";
const PYPI_INDEX: &str = "https://pypi.tuna.tsinghua.edu.cn/simple/";

/// SeekDB 包管理器（使用 pyseekdb，见 https://github.com/oceanbase/pyseekdb）
pub struct SeekDbPackage<'a> {
    python_env: &'a PythonEnv,
}

impl<'a> SeekDbPackage<'a> {
    /// 创建新的 SeekDB 包管理器
    pub fn new(python_env: &'a PythonEnv) -> Self {
        Self { python_env }
    }

    /// 检查 pyseekdb 包是否已安装
    pub fn is_installed(&self) -> Result<bool> {
        log::info!("🔍 检查 pyseekdb 包是否已安装...");

        let output = Command::new(self.python_env.get_python_executable())
            .arg("-c")
            .arg("import pyseekdb; print(pyseekdb.__file__)")
            .output();

        match output {
            Ok(output) => {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout);
                    log::info!("✅ pyseekdb 已安装: {}", path.trim());
                    Ok(true)
                } else {
                    log::info!("⚠️  pyseekdb 未安装");
                    Ok(false)
                }
            }
            Err(e) => {
                log::warn!("检查 pyseekdb 安装状态失败: {}", e);
                Ok(false)
            }
        }
    }

    /// 安装 pyseekdb 包
    pub fn install(&self) -> Result<()> {
        log::info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        log::info!("  📦 安装 pyseekdb 包");
        log::info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        log::info!("   包名: {}", PYSEEKDB_PACKAGE);
        log::info!("   镜像: {}", PYPI_INDEX);
        log::info!("");
        log::info!("这可能需要几分钟时间，请稍候...");

        let python_executable = self.python_env.get_python_executable();

        // 首先升级 pip
        log::info!("🔧 升级 pip...");
        let upgrade_pip = Command::new(python_executable)
            .arg("-m")
            .arg("pip")
            .arg("install")
            .arg("--upgrade")
            .arg("pip")
            .arg("-i")
            .arg(PYPI_INDEX)
            .status();

        match upgrade_pip {
            Ok(status) if status.success() => {
                log::info!("✅ pip 升级完成");
            }
            _ => {
                log::warn!("⚠️  pip 升级失败，继续安装 pyseekdb...");
            }
        }

        // 安装 pyseekdb
        log::info!("📦 安装 {}...", PYSEEKDB_PACKAGE);

        let status = Command::new(python_executable)
            .arg("-m")
            .arg("pip")
            .arg("install")
            .arg(PYSEEKDB_PACKAGE)
            .arg("-i")
            .arg(PYPI_INDEX)
            .status()
            .map_err(|e| anyhow!("执行 pip install 失败: {}", e))?;

        if !status.success() {
            return Err(anyhow!(
                "pyseekdb 安装失败（退出码: {:?}）\n\n\
                请检查：\n\
                1. 网络连接是否正常\n\
                2. 镜像源是否可访问: {}\n\
                3. Python 版本 >= 3.11\n\n\
                您也可以手动安装：\n\
                {:?} -m pip install {} -i {}",
                status.code(),
                PYPI_INDEX,
                python_executable,
                PYSEEKDB_PACKAGE,
                PYPI_INDEX
            ));
        }

        log::info!("✅ pyseekdb 安装完成");
        Ok(())
    }

    /// 验证 pyseekdb 安装
    pub fn verify(&self) -> Result<()> {
        log::info!("🔍 验证 pyseekdb 安装...");

        let output = Command::new(self.python_env.get_python_executable())
            .arg("-c")
            .arg("import pyseekdb; print('pyseekdb location:', pyseekdb.__file__)")
            .output()
            .map_err(|e| anyhow!("验证 pyseekdb 失败: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(anyhow!(
                "pyseekdb 验证失败\n\n\
                无法导入 pyseekdb 模块\n\
                错误信息: {}\n\n\
                请尝试重新安装：\n\
                {:?} -m pip install --force-reinstall {} -i {}",
                stderr.trim(),
                self.python_env.get_python_executable(),
                PYSEEKDB_PACKAGE,
                PYPI_INDEX
            ));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        log::info!("✅ pyseekdb 验证通过");
        for line in stdout.lines() {
            log::info!("   {}", line);
        }

        Ok(())
    }

    /// 获取 pyseekdb 版本信息
    pub fn get_version_info(&self) -> Result<String> {
        let output = Command::new(self.python_env.get_python_executable())
            .arg("-c")
            .arg(
                "try:\n    import pyseekdb; print(getattr(pyseekdb, '__version__', 'unknown'))\nexcept Exception:\n    print('unknown')",
            )
            .output()
            .map_err(|e| anyhow!("获取版本信息失败: {}", e))?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            Ok("unknown".to_string())
        }
    }
}

