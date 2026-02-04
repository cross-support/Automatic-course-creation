# Automatic-course-creation

## プロジェクト紹介 (Project Overview)

入力されたデータを**OpenAI API**で要約・構造化し、**Google Slides API**を使用してGoogleスライド（Google Slides）を自動的に生成します。

**主な機能**
- **AIコンテンツ生成**: OpenAI(GPT)を活用したスライド構成資料およびレイアウト生成
- **スライド生成**: **Google Slides API**を活用して、座標ベースでテキストボックスや図形を精密に配置

## デモ動画 (Demo Video)
[![Demo Video](https://img.youtube.com/vi/OoEsnP-VbK8/0.jpg)](https://www.youtube.com/watch?v=OoEsnP-VbK8)

## 技術スタック (Tech Stack)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&labelColor=3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Google Cloud](https://img.shields.io/badge/Google_Cloud_Platform-4285F4?style=flat&logo=google-cloud&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)

- **Framework**: FastAPI, Uvicorn
- **Libraries**: google-api-python-client, openai, pydantic, pandas

## 環境設定 (Prerequisites)
プロジェクトを実行する前に、以下の必須ファイルを**ルートディレクトリ**に準備する必要があります。

1. **Google Cloud Credentials**：Google Cloud Platformで発行された`credentials.json`ファイルをプロジェクトのルートに配置してください。
2. **Environment Variables**: `。env.example` ファイル名を`。env`に変更し、APIキーを設定してください。

## インストールと実行 (Installation & Run)

### プロジェクトクローン (Clone Project)
まず、プロジェクトのコードをローカル環境にクローンします。

```shell
git clone https://github.com/cross-support/Automatic-course-creation
```

### 仮想環境の作成と有効化

仮想環境の作成

```shell
python -m venv venv
```

仮想環境の活性化

- Windows: venv\Scripts\activate
- Mac/Linux: source venv/bin/activate

### 依存ライブラリのインストール

```shell
pip install --upgrade pip
pip install -r requirements.txt
```

### サーバーを実行する

```shell
python main.py
```

### 正常動作の確認

```shell
http://127.0.0.1:8000
```
