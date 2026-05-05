"""
测试套件入口

包含所有单元测试，覆盖系统核心组件：
- utils/json_parser.py：LLM 响应 JSON 提取
- services/embedding.py：轻量相关性评分
- services/rag.py：RAG 证据召回
- agents/citation.py：引用校验
- services/query_expander.py：查询扩展

运行方式：
    cd backend
    source venv/bin/activate
    pytest tests/ -v
"""
