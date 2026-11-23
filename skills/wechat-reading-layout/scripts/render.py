#!/usr/bin/env python3
"""Render a structured Chinese WeChat article and a local browser preview."""

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_THEME = {"accent": "#315f4d", "body": "#313936", "surface": "#f5f7f1"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def required_text(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} 需要填写文字")
    return value


def inline(value):
    escaped = html.escape(value)
    return re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", escaped)


def paragraph(text, style):
    return f'<p style="{style}">{text}</p>'


def image_markup(item, source_dir, assets, *, cover=False):
    source = (source_dir / required_text(item, "file")).resolve()
    if not source.is_relative_to(source_dir) or source.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError("图片应为清单目录内的 JPG、PNG、WebP 或 GIF 文件")
    if not source.is_file():
        raise ValueError(f"找不到图片：{item['file']}")
    alt = html.escape(required_text(item, "alt"))
    if source not in assets:
        assets[source] = f"assets/image-{len(assets) + 1:02d}{source.suffix.lower()}"
    width = "display:inline-block;width:132px;max-width:100%;margin:0 auto;vertical-align:top;" if cover else (
        "display:block;width:100%;max-width:100%;"
    )
    markup = paragraph(
        f'<img src="{assets[source]}" alt="{alt}" style="{width}height:auto;border-radius:10px;">',
        "margin:0 0 12px;text-align:center;" if cover else "margin:22px 0 10px;",
    )
    if item.get("caption"):
        markup += paragraph(inline(item["caption"]), "margin:0 0 20px;font-size:13px;line-height:1.7;color:#657366;")
    return markup


def render(article, source_dir):
    title = required_text(article, "title")
    author = article.get("author", "")
    if not isinstance(author, str):
        raise ValueError("author 应为文字")
    blocks = article.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("blocks 需要包含至少一个正文组件")
    theme = {**DEFAULT_THEME, **article.get("theme", {})}
    for field in DEFAULT_THEME:
        value = theme[field]
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError(f"主题颜色 {field} 应为六位十六进制颜色")
    accent, body, surface = (theme[field] for field in ("accent", "body", "surface"))
    prose = f"margin:0 0 18px;color:{body};font-size:16px;line-height:1.9;word-wrap:break-word;"
    note = "margin:0 0 12px;color:#657366;font-size:13px;line-height:1.7;"
    source_card = f"margin:28px 0 0;padding:18px;background-color:{surface};border-radius:10px;"
    fragments = ['<section style="padding:0 12px;">']
    assets = {}

    if article.get("notice"):
        fragments.append(paragraph(inline(article["notice"]), note))
    if article.get("overview"):
        fragments.append(image_markup(article["overview"], source_dir, assets))

    for block in blocks:
        kind = required_text(block, "type")
        if kind == "heading":
            level = block.get("level", 2)
            if level not in (2, 3):
                raise ValueError("小标题级别应为 2 或 3")
            size = 22 if level == 2 else 17
            text = inline(required_text(block, "text"))
            fragments.append(f'<h{level} style="margin:30px 0 15px;color:{accent};font-size:{size}px;'
                             f'line-height:1.5;font-weight:bold;">{text}</h{level}>')
        elif kind == "paragraph":
            fragments.append(paragraph(inline(required_text(block, "text")), prose))
        elif kind == "quote":
            text = inline(required_text(block, "text"))
            fragments.append(f'<blockquote style="margin:22px 0;padding:14px;border-left:3px solid {accent};'
                             f'background-color:{surface};">{paragraph(text, prose.replace("18px", "0"))}</blockquote>')
        elif kind == "list":
            tag = "ol" if block.get("ordered") else "ul"
            items = block.get("items")
            if not isinstance(items, list) or not items or not all(isinstance(item, str) for item in items):
                raise ValueError("列表 items 需要包含至少一条文字")
            content = "".join(f"<li>{inline(item)}</li>" for item in items)
            fragments.append(f'<{tag} style="{prose}padding-left:1.4em;">{content}</{tag}>')
        elif kind == "image":
            fragments.append(image_markup(block, source_dir, assets))
        elif kind == "source":
            text = inline(required_text(block, "text"))
            url = block.get("url")
            if url:
                parsed = urlsplit(url)
                if parsed.scheme != "https" or not parsed.netloc or parsed.username:
                    raise ValueError("来源链接需使用公开的 HTTPS 地址")
                text = f'<a href="{html.escape(url)}" style="color:{accent};">{text}</a>'
            fragments.append(paragraph(text, note))
        else:
            raise ValueError(f"未知正文组件：{kind}")

    if article.get("book"):
        book = article["book"]
        book_title = html.escape(required_text(book, "title"))
        metadata = " · ".join(html.escape(book[key]) for key in ("author", "publisher", "edition") if book.get(key))
        centered = "text-align:center;margin:0 0 12px;"
        fragments.append(f'<section style="{source_card}text-align:center;">')
        fragments.append(paragraph("继续读原书", centered + f"font-size:17px;font-weight:bold;color:{accent};"))
        if book.get("cover"):
            fragments.append(image_markup(book["cover"], source_dir, assets, cover=True))
        fragments.append(paragraph(f"《{book_title}》", centered + f"font-weight:bold;color:{accent};"))
        if metadata:
            fragments.append(paragraph(metadata, note + "text-align:center;margin-bottom:0;"))
        fragments.append("</section>")
    fragments.append("</section>")
    fragment = "\n".join(fragments)

    credit = paragraph(html.escape(author), note) if author else ""
    preview = (
        '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{html.escape(title)}</title></head>\n'
        '<body style="margin:0 auto;max-width:390px;padding:20px 0 30px;'
        'font-family:system-ui,sans-serif;background-color:#fff;">\n'
        f'<header style="padding:0 12px;"><h1 style="margin:0 0 16px;font-size:24px;'
        f'line-height:1.45;color:{body};">{html.escape(title)}</h1>{credit}</header>\n'
        f'{fragment}\n</body></html>\n'
    )
    return fragment, preview, assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="UTF-8 JSON 文章清单")
    parser.add_argument("--output", type=Path, required=True, help="输出目录")
    args = parser.parse_args()
    try:
        manifest = args.manifest.resolve()
        article = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(article, dict):
            raise ValueError("清单根节点必须是 JSON 对象")
        fragment, preview, assets = render(article, manifest.parent)
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        for source, relative in assets.items():
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.resolve() != source:
                shutil.copyfile(source, target)
        (output / "article.html").write_text(fragment + "\n", encoding="utf-8")
        (output / "preview.html").write_text(preview, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(2, f"排版失败：{error}\n")
    print(f"已生成 {output / 'article.html'} 和 {output / 'preview.html'}")


if __name__ == "__main__":
    main()
