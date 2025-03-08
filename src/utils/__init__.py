"""
工具类模块
"""

# 导入所有工具模块
from .file_utils import *
from .table_utils import *
from .docx_utils import *
from .text_utils import *
from .similarity_utils import *
from .cleanup_utils import *
from .ai_utils import ai_answer, add_first_line_indent

# 创建模块别名以保持兼容性
file_path = file_utils
table_about = table_utils
docx_to_md = docx_utils
smart_divide = text_utils
same_find = similarity_utils 