"""
シンプルなFastAPI + OpenAI統合サーバー
依存関係の問題を回避した最小構成版
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 環境変数読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリ初期化
app = FastAPI(title="Famoly Drive API", version="2.0.0")

# CORS設定（開発・プロダクション対応）
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# OpenAIクライアント初期化（エラーハンドリング付き）
openai_client = None
try:
    if OPENAI_API_KEY and OPENAI_API_KEY.startswith('sk-'):
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
    else:
        logger.warning("OpenAI API key not provided or invalid format")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    openai_client = None

# リクエスト/レスポンスモデル
class QuizRequest(BaseModel):
    spot_name: str
    spot_description: str
    difficulty: str = "中学生"

class QuizResponse(BaseModel):
    success: bool
    quiz: Optional[Dict]
    generated_by: str

# ルートエンドポイント
@app.get("/")
async def root():
    try:
        return {
            "message": "Famoly Drive API is running",
            "openai_configured": bool(openai_client),
            "version": "2.0.0",
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Root endpoint error: {e}")
        return {
            "message": "Famoly Drive API",
            "status": "error",
            "error": str(e)
        }

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "openai_available": bool(openai_client)
    }

# AIクイズ生成エンドポイント
@app.post("/api/v1/quizzes/generate-ai", response_model=QuizResponse)
async def generate_ai_quiz(request: QuizRequest):
    """OpenAI APIを使用した動的クイズ生成"""
    
    # OpenAI APIが設定されていない場合はフォールバック
    if not openai_client:
        logger.warning("OpenAI API key not configured, using fallback")
        return QuizResponse(
            success=True,
            quiz=_get_fallback_quiz(request.spot_name, request.difficulty),
            generated_by="fallback"
        )
    
    try:
        # クイズ生成
        quiz_data = await _generate_quiz_with_openai(
            request.spot_name,
            request.spot_description,
            request.difficulty
        )
        
        return QuizResponse(
            success=True,
            quiz=quiz_data,
            generated_by="openai"
        )
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return QuizResponse(
            success=True,
            quiz=_get_fallback_quiz(request.spot_name, request.difficulty),
            generated_by="fallback"
        )

async def _generate_quiz_with_openai(spot_name: str, spot_description: str, difficulty: str) -> Dict:
    """OpenAIでクイズ生成"""
    
    # ポイント設定
    points = {"小学生": 10, "中学生": 15, "高校生": 20}.get(difficulty, 15)
    
    # プロンプト生成
    prompt = f"""
{spot_name}について{difficulty}レベルのクイズを1問作成してください。

スポット情報: {spot_description}

以下の形式で回答:
問題: [4択問題文]
1. [選択肢1]
2. [選択肢2]
3. [選択肢3]
4. [選択肢4]
正解: [1-4の数字]
解説: [簡潔な解説文]
""".strip()
    
    # OpenAI API呼び出し
    response = await openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=OPENAI_MAX_TOKENS,
        temperature=OPENAI_TEMPERATURE
    )
    
    # レスポンス解析
    quiz_text = response.choices[0].message.content
    parsed_quiz = _parse_quiz_response(quiz_text, points)
    
    # 使用トークン数をログ
    logger.info(f"Quiz generated for {spot_name} - Tokens: {response.usage.total_tokens}")
    
    return parsed_quiz

def _parse_quiz_response(response: str, points: int) -> Dict:
    """OpenAI回答を構造化データに変換"""
    try:
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        question = ""
        options = []
        correct_answer = 0
        explanation = ""
        
        for line in lines:
            if line.startswith('問題:'):
                question = line.replace('問題:', '').strip()
            elif line.startswith(('1.', '2.', '3.', '4.')):
                options.append(line[2:].strip())
            elif line.startswith('正解:'):
                try:
                    correct_answer = int(line.replace('正解:', '').strip()) - 1
                except ValueError:
                    correct_answer = 0
            elif line.startswith('解説:'):
                explanation = line.replace('解説:', '').strip()
        
        return {
            "question": question or "この場所について正しいものはどれでしょう？",
            "options": options if len(options) == 4 else [
                "歴史的に重要な場所である",
                "最近建設された建物である",
                "海外にある場所である",
                "架空の場所である"
            ],
            "correct_answer": max(0, min(3, correct_answer)),
            "explanation": explanation or "歴史的に重要な場所として知られています。",
            "points": points
        }
        
    except Exception as e:
        logger.error(f"Quiz parsing error: {e}")
        return _get_fallback_quiz("", 15)

def _get_fallback_quiz(spot_name: str, difficulty: str) -> Dict:
    """フォールバッククイズ生成"""
    points = {"小学生": 10, "中学生": 15, "高校生": 20}.get(difficulty, 15)
    
    # スポット名に基づくクイズ生成
    if "大仏" in spot_name:
        return {
            "question": f"{spot_name}について正しいものはどれでしょう？",
            "options": [
                "13世紀に建立された国宝である",
                "最近作られたレプリカである",
                "海外から輸入された仏像である",
                "実際には存在しない伝説上の仏像である"
            ],
            "correct_answer": 0,
            "explanation": f"{spot_name}は鎌倉時代に建立された、日本を代表する文化財です。",
            "points": points
        }
    elif "八幡宮" in spot_name:
        return {
            "question": f"{spot_name}と関係が深い人物は誰でしょう？",
            "options": [
                "源頼朝",
                "織田信長",
                "豊臣秀吉",
                "徳川家康"
            ],
            "correct_answer": 0,
            "explanation": f"{spot_name}は源頼朝によって鎌倉幕府の守護神として崇敬されました。",
            "points": points
        }
    else:
        return {
            "question": f"{spot_name}について正しいものはどれでしょう？",
            "options": [
                "歴史的に重要な場所である",
                "最近建設された観光地である",
                "架空の場所である",
                "海外にある場所である"
            ],
            "correct_answer": 0,
            "explanation": f"{spot_name}は長い歴史を持つ重要な文化遺産です。",
            "points": points
        }

# APIの使用統計エンドポイント
@app.get("/api/v1/stats/usage")
async def get_usage_stats():
    """API使用統計（コスト管理用）"""
    return {
        "model": OPENAI_MODEL,
        "estimated_cost_per_quiz": 0.001,  # 約0.1円
        "max_tokens": OPENAI_MAX_TOKENS,
        "temperature": OPENAI_TEMPERATURE,
        "api_configured": bool(OPENAI_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)