# GO EVENT LOG — 自動更新版

Pokémon GO公式ニュースを定期巡回し、イベント関連記事を発表日順に掲載する非公式サイトです。

## 自動更新の仕組み

- GitHub Actionsが6時間ごとに `https://pokemongo.com/news` を確認
- 新しいイベント関連記事を `data/events.json` に追加
- 既存データを残したまま統合
- GitHub Pagesへ自動デプロイ
- 手動実行はGitHubの **Actions → Update official events and deploy → Run workflow**

## 公開手順

1. このフォルダの中身を新しいGitHubリポジトリの `main` ブランチへアップロードします。
2. GitHubで **Settings → Pages → Source** を **GitHub Actions** に変更します。
3. **Actions** タブでワークフローの実行を許可します。
4. `Update official events and deploy` を一度手動実行します。
5. 実行完了後、PagesのURLで公開されます。

GitHub Actionsの定期実行時刻はUTCです。現在の設定 `17 */6 * * *` は6時間ごとで、混雑により開始が少し遅れる場合があります。

## ローカル確認

`fetch()` でJSONを読むため、`index.html` を直接ダブルクリックせずWebサーバー経由で開きます。

```bash
python -m http.server 8000
```

その後 `http://localhost:8000` を開きます。

## 注意点

公式ページの構造変更により取得処理が止まる可能性があります。取得失敗時は既存のイベントデータを消さず、ワークフローを失敗させます。また、開催日時の自動抽出は誤判定を避けるため控えめで、解析できない記事は「公式ページで確認」と表示します。

Pokémon GO、Pokémonおよび各名称は権利者に帰属します。本サイトは非公式ファンサイトです。
