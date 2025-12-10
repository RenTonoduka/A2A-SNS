# /session コマンド

Xへのログインセッションを管理する

## 使用方法

```
/session           # セッション状態確認
/session info      # 詳細情報表示
/session verify    # ログイン状態検証
/session login     # ログイン開始（ブラウザ起動）
/session clear     # セッションクリア
```

## 実行手順

### セッション状態確認

```bash
python session_manager.py info
```

出力例:
```json
{
  "session_name": "default",
  "saved_at": "2024-01-01T00:00:00",
  "storage_file": "sessions/default_storage.json"
}
```

### ログイン状態検証

```bash
python session_manager.py verify
```

出力:
- ✅ ログイン状態: 有効
- ❌ ログイン状態: 無効（再ログインが必要）

### ログイン開始

```bash
python session_manager.py login
```

⚠️ **注意**: ブラウザが起動します。手動でログインしてください。

手順:
1. ブラウザが開く
2. X（Twitter）のログインページが表示
3. 手動でログイン（ID/パスワード、2FA等）
4. ホームページにリダイレクトされたら自動保存
5. ブラウザが閉じる

### セッションクリア

```bash
python session_manager.py clear
```

⚠️ 次回の抽出時に再ログインが必要になります。

---

## セッションファイル

```
sessions/
├── default_session.json      # メタデータ
└── default_storage.json      # Playwright storage state
```

## 複数アカウント対応

```bash
# 別名でセッション作成
python session_manager.py login --session work
python session_manager.py login --session personal

# 抽出時にセッション指定
python post_extractor.py elonmusk --session work
```

---

## トラブルシューティング

### セッションが無効になる原因

1. **長期間未使用**: Xがセッションを無効化
2. **パスワード変更**: 全セッションが無効化
3. **アカウント制限**: スクレイピング検出

### 対処法

```bash
# 1. セッションクリア
python session_manager.py clear

# 2. 再ログイン
python session_manager.py login

# 3. 検証
python session_manager.py verify
```

---

## 出力例

```
📋 Session Info
━━━━━━━━━━━━━━━━━━━━━━━━

セッション名: default
保存日時: 2024-01-01 00:00:00
ストレージ: sessions/default_storage.json

✅ セッション有効
```

---

## 関連コマンド

- `/extract` - ポスト抽出
- `/analyze` - ポスト分析
