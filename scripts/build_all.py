import os
import sys
import subprocess
import logging
import shutil
from datetime import datetime

# 添加项目根目录到 Python 路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    print(f"已添加项目根目录到 Python 路径: {root_dir}")

def setup_logging():
    """设置日志记录"""
    log_dir = "build_logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def run_command(command, cwd=None):
    """运行命令并返回结果"""
    logging.info(f"执行命令: {command}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"命令输出:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"命令执行失败:\n{e.stderr}")
        return False

def ensure_icon_files():
    """确保图标文件存在并且格式正确"""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    material_dir = os.path.join(root_dir, "material")
    os.makedirs(material_dir, exist_ok=True)
    
    icon_files = {
        "1-logo.ico": "安装程序图标",
        "2-logo.ico": "主程序图标"
    }
    
    for icon_file, description in icon_files.items():
        icon_path = os.path.join(material_dir, icon_file)
        if not os.path.exists(icon_path):
            logging.error(f"缺少{description}: {icon_path}")
            return False
        
        # 检查图标文件大小
        size = os.path.getsize(icon_path)
        if size < 1024:  # 小于1KB可能是无效图标
            logging.error(f"{description}文件过小，可能无效: {size} 字节")
            return False
            
        logging.info(f"找到{description}: {icon_path} ({size} 字节)")
    
    return True

def build_main_program():
    """打包主程序（B.exe）"""
    logging.info("开始打包主程序...")
    
    # 检查图标文件
    if not ensure_icon_files():
        return False
    
    # 切换到项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    
    # 清理旧的构建文件
    if os.path.exists("build"):
        run_command("rmdir /s /q build")
    if os.path.exists("dist"):
        run_command("rmdir /s /q dist")
    
    # 打包主程序
    if not run_command("pyinstaller --noconfirm ai_review.spec"):
        return False
    
    # 检查主程序是否生成成功
    main_exe = os.path.join(root_dir, "dist", "AI审校助手.exe")
    if not os.path.exists(main_exe):
        logging.error(f"主程序文件未生成: {main_exe}")
        return False
    
    # 验证生成的exe
    file_size = os.path.getsize(main_exe)
    logging.info(f"主程序打包成功:")
    logging.info(f"  路径: {main_exe}")
    logging.info(f"  大小: {file_size:,} 字节")
    logging.info(f"  修改时间: {datetime.fromtimestamp(os.path.getmtime(main_exe))}")
    
    return True

def build_installer():
    """打包安装程序"""
    logging.info("开始打包安装程序...")
    
    # 获取路径
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(scripts_dir)
    dist_dir = os.path.join(root_dir, "dist")  # 使用项目根目录下的dist
    
    # 检查主程序是否存在
    main_exe = os.path.join(dist_dir, "AI审校助手.exe")
    if not os.path.exists(main_exe):
        logging.error(f"找不到主程序: {main_exe}")
        return False
    
    # 切换到scripts目录
    os.chdir(scripts_dir)
    
    # 清理旧的构建文件
    if os.path.exists("build"):
        run_command("rmdir /s /q build")
    
    # 打包安装程序，直接输出到项目的dist目录
    success = run_command(f"pyinstaller --noconfirm --distpath {dist_dir} installer.spec")
    
    if success:
        installer_exe = os.path.join(dist_dir, "安装程序.exe")
        if os.path.exists(installer_exe):
            file_size = os.path.getsize(installer_exe)
            logging.info(f"安装程序打包成功:")
            logging.info(f"  路径: {installer_exe}")
            logging.info(f"  大小: {file_size:,} 字节")
            logging.info(f"  修改时间: {datetime.fromtimestamp(os.path.getmtime(installer_exe))}")
        else:
            logging.error("安装程序文件未生成")
            success = False
    
    return success

def main():
    """主函数"""
    log_file = setup_logging()
    logging.info("开始构建过程...")
    
    try:
        # 1. 打包主程序（B.exe）
        if not build_main_program():
            logging.error("主程序打包失败")
            return False
        
        # 2. 打包安装程序（A.exe）
        if not build_installer():
            logging.error("安装程序打包失败")
            return False
        
        logging.info("\n构建过程完成!")
        logging.info("生成的文件:")
        logging.info("1. 主程序: dist/AI审校助手.exe")
        logging.info("2. 安装程序: scripts/dist/安装程序.exe")
        logging.info(f"\n日志文件保存在: {log_file}")
        return True
        
    except Exception as e:
        logging.error(f"构建过程出错: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 