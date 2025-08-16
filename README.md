# 🚀 Famoly Drive Backend API

## 概要

Famoly Drive（家族向け教育ドライブアプリ）のバックエンドAPI。
OpenAI APIを使用した動的クイズ生成機能を提供します。

## 機能

- 🤖 OpenAI統合による動的クイズ生成
- 🔄 フォールバック機能（API障害時の安全動作）
- ⚡ FastAPI による高速API
- 🌐 CORS対応（開発・プロダクション環境）

## 環境変数

```bash
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=300
OPENAI_TEMPERATURE=0.7
ALLOWED_ORIGINS=http://localhost:3001,https://your-frontend-domain.azurestaticapps.net
```

## 起動方法

### ローカル開発
```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Azure App Service
- Runtime: Python 3.11
- Startup command: `python -m uvicorn app:app --host 0.0.0.0`

## API エンドポイント

### ヘルスチェック
```
GET /health
```

### AIクイズ生成
```
POST /api/v1/quizzes/generate-ai
```

### 使用統計
```
GET /api/v1/stats/usage
```

## デプロイ準備済み ✅

このバックエンドはAzure環境でのデプロイ用に最適化されています。

---

## 🔄 バックアップ情報
以前のCRUD顧客管理アプリは `backup-crud-app` ブランチに保存されています。