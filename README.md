# 招聘防骗系统 (Job Scam Guard)

基于规则引擎的招聘诈骗风险识别 MVP，对应「招聘防骗系统可行性分析」的落地验证版本。

## 功能

- **文本风险检测**：分析职位描述、聊天记录或任意文本
- **8 类骗局规则**：收费陷阱、脱离平台、帮信/工具人、钓鱼软件、仿冒企业、资金异常、过度索证、传销拉人头
- **链接检测**：识别仿冒招聘域名与可疑 URL 结构
- **风险评分**：0–100 分，低/中/高危三级
- **本地举报**：记录举报条目至 `data/reports.jsonl`

## 快速开始

```bash
cd C:\Users\YYX\Projects\job-scam-guard
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

浏览器打开：**http://127.0.0.1:8765**

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 文本检测 `{ "text": "...", "content_type": "job\|chat\|general" }` |
| POST | `/api/analyze/url` | 链接检测 `{ "url": "..." }` |
| POST | `/api/report` | 提交举报 |
| GET | `/api/patterns` | 查看规则库摘要 |
| GET | `/api/health` | 健康检查 |

## 项目结构

```
job-scam-guard/
├── app/
│   ├── engine.py      # 检测引擎
│   └── main.py        # FastAPI 服务
├── data/
│   ├── patterns.json  # 规则库（可扩展）
│   └── reports.jsonl  # 举报记录（运行时生成）
├── static/            # Web 前端
├── run.py
└── requirements.txt
```

## 后续扩展方向

1. 接入 LLM 做语义级变种话术识别
2. 企业工商/招聘邮箱域名核验 API
3. 图数据库关联同一骗子多账号
4. 与招聘平台对接 webhook 实时拦截

## 免责声明

本系统为技术验证 MVP，检测结果仅供参考，不能替代平台官方风控与法律判断。
