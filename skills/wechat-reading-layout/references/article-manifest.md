# 排版清单
清单是 UTF-8 JSON，包含 `title`（文章标题）和 `blocks`（有序正文组件）。`author` 是可选署名。`notice` 是图前阅读提示。`overview` 是可选首屏图，字段与图片组件相同。`book` 是可选文末原书卡。
| 组件 `type` | 字段 |
| --- | --- |
| `heading` | `text`，可选 `level` 为 2 或 3 |
| `paragraph` / `quote` | `text`，支持 `**重点**` |
| `list` | `items` 为文字数组，可加 `ordered: true` |
| `image` | `file` 为清单目录里的相对路径，`alt` 为替代文字，可选 `caption` 为图注 |
| `source` | `text` 为来源名称，可选 `url` 为 HTTPS 链接 |
原书卡支持 `title`、`author`、`publisher`、`edition` 和可选 `cover`。有书封时，`cover` 使用与图片组件相同的字段。可选 `theme` 接受 `accent`、`body`、`surface`，值为六位十六进制颜色。
运行 `python skills/wechat-reading-layout/scripts/render.py <清单.json> --output <输出目录>`。合上目录一起搬运时，预览使用 `assets/` 中的相对图片路径。
