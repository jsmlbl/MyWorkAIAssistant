# MyWorkAIAssistant
用于记录自己工作记录的AI搜索工具

## 依赖安装

```bash
pip install -r requirements.txt
```

## 数据库配置
- 数据库类型：TiDB
- 地址：192.168.5.124
- 端口：4000
- 用户名：root
- 数据库名：myassistant
- 密码：无（如有请在 main.py 中修改）

## 启动后端（FastAPI）
```bash
uvicorn main:app --reload
```

## 启动前端（Streamlit）
```bash
streamlit run frontend.py
```

## 主要功能
- 任务管理（增删改查、完成状态、标签、优先级）
- 附件管理（图片、Excel、PDF、Word等文件上传与下载）
- 预留AI助手接口（后续可集成DeepSeek等大模型）
