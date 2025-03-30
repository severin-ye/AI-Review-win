import os
import sys

class PathManager:
    """路径管理器，负责管理所有项目路径"""
    
    _instance = None
    
    def __new__(cls):
        """确保PathManager是单例"""
        if cls._instance is None:
            cls._instance = super(PathManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化路径管理器"""
        # 避免重复初始化
        if getattr(self, '_initialized', False):
            return
            
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            self.project_root = os.path.dirname(sys.executable)
        else:
            current_file = os.path.abspath(__file__)
            self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # 配置目录
        self.config_dir = os.path.join(self.project_root, "config")
        self.settings_dir = os.path.join(self.config_dir, "settings")
        
        # 基础目录
        self.hide_file_dir = os.path.join(self.project_root, "hide_file")
        self.logs_dir = os.path.join(self.project_root, "logs")
        self.material_dir = os.path.join(self.project_root, "material")
        self.src_dir = os.path.join(self.project_root, "src")
        
        # 中间文件目录 - 使用英文目录名
        self.temp_files_dir = os.path.join(self.hide_file_dir, "temp_files")
        
        # 工作目录 - 使用英文目录名
        self.original_files_dir = os.path.join(self.temp_files_dir, "original_files")
        self.reviewed_files_dir = os.path.join(self.temp_files_dir, "reviewed_files")
        
        # 配置文件目录 - 使用英文目录名
        self.config_files_dir = os.path.join(self.hide_file_dir, "config_files")
        self.config_file = os.path.join(self.config_files_dir, "config.json")
        self.theme_file = os.path.join(self.settings_dir, "theme.json")
        
        # 医学参考文档目录 - 使用英文目录名
        self.medical_docs_dir = os.path.join(self.hide_file_dir, "medical_reference")
        
        # 资源文件
        self.icon_file = os.path.join(self.material_dir, "icon.ico")
        
        # 确保必要的目录存在
        self._ensure_directories()
        
        # 标记为已初始化
        self._initialized = True
    
    def _ensure_directories(self):
        """确保所有必要的目录都存在"""
        directories = [
            self.config_dir,
            self.settings_dir,
            self.hide_file_dir,
            self.logs_dir,
            self.material_dir,
            self.temp_files_dir,
            self.original_files_dir,
            self.reviewed_files_dir,
            self.config_files_dir,
            self.medical_docs_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_log_file(self, date_str=None):
        """获取日志文件路径"""
        if date_str is None:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.logs_dir, f'app_{date_str}.log')
    
    def get_reviewed_md_files(self):
        """获取所有审校后的md文件"""
        pattern = os.path.join(self.temp_files_dir, "**/*_审校后_.md")
        import glob
        return glob.glob(pattern, recursive=True)
    
    def get_app_config_path(self):
        """获取应用配置文件路径"""
        return self.config_file
    
    def get_theme_config(self):
        """获取主题配置文件路径"""
        return self.theme_file
    
    def get_default_output_dir(self):
        """获取默认输出目录"""
        return self.reviewed_files_dir
    
    def get_medical_docs_dir(self):
        """获取医学参考文档目录"""
        return self.medical_docs_dir
    
    def generate_file_paths(self, file_name):
        """生成文件相关的所有路径"""
        base_name = os.path.splitext(file_name)[0]
        
        return {
            'begin_path': os.path.join(self.original_files_dir, file_name),
            'no_table': os.path.join(self.temp_files_dir, f"{base_name}_无表格_.docx"),
            'path_extract': os.path.join(self.temp_files_dir, f"{base_name}_表格提取_.json"),
            'md_path': os.path.join(self.temp_files_dir, f"{base_name}_.md"),
            'ai_path': os.path.join(self.temp_files_dir, f"{base_name}_审校后_.md"),
            'word_path_1': os.path.join(self.temp_files_dir, f"{base_name}_审校修订1_.docx"),
            'word_path_2': os.path.join(self.temp_files_dir, f"{base_name}_审校修订2_.docx"),
            'final_path_1': os.path.join(self.reviewed_files_dir, f"{base_name}_审校修订1_.docx"),
            'final_path_2': os.path.join(self.reviewed_files_dir, f"{base_name}_审校修订2_.docx"),
            'select_path_1': os.path.join(self.temp_files_dir, f"{base_name}_选择修订1_.md"),
            'select_path_2': os.path.join(self.temp_files_dir, f"{base_name}_选择修订2_.md")
        }

# 单例路径管理器
path_manager = PathManager() 