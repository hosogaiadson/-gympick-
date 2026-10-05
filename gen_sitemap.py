#!/usr/bin/env python3
"""
sitemap.xml の <lastmod> を、各ページの「最後に中身が変わった日」に合わせて書き直す。

- 日付 = そのHTMLファイルを最後に変えた git コミットの日（日本時間）
- コミットの件名に [sitewide] が付いているものは数えない
  （広告表記・フッターなど、全ページ共通部分だけを一斉に直したコミット。
   これを数えると lastmod がまた全ページ同じ日付に揃ってしまう）
- まだコミットしていない変更があるファイルは、今日の日付にして警告を出す
- <loc> の並び・changefreq・priority は今の sitemap.xml のまま残す

使い方（中身を直してコミットした後に実行 → sitemap.xml をコミットして push）:
    python3 gen_sitemap.py
    git add sitemap.xml && git commit -m "sitemapのlastmodを更新" && git push
"""
import datetime
import os
import re
import subprocess
from pathlib import Path

SITE = Path(__file__).resolve().parent
SITEMAP = SITE / "sitemap.xml"
BASE = "https://gympick.jp/"
SKIP_MARK = "[sitewide]"
ENV = dict(os.environ, TZ="Asia/Tokyo")


def git(*args):
    return subprocess.run(["git", *args], cwd=SITE, env=ENV, capture_output=True,
                          text=True, check=True).stdout


def last_content_date(filename):
    """[sitewide] 以外で、そのファイルを最後に変えたコミットの日付（JST）"""
    log = git("log", "--format=%cd\t%s", "--date=format-local:%Y-%m-%d", "--", filename)
    for line in log.splitlines():
        date, _, subject = line.partition("\t")
        if SKIP_MARK not in subject:
            return date
    return None


def main():
    xml = SITEMAP.read_text(encoding="utf-8")
    dirty = set(git("status", "--porcelain").split()[1::2])
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    seen, changed = set(), 0

    def repl(m):
        nonlocal changed
        loc, old = m.group(2), m.group(4)
        path = loc[len(BASE):] or "index.html"
        seen.add(path)
        if not (SITE / path).exists():
            print(f"⚠️ ファイルが無い: {loc}")
            return m.group(0)
        if path in dirty:
            print(f"⚠️ 未コミットの変更あり → 今日の日付にする: {path}")
            new = today
        else:
            new = last_content_date(path) or old
        if new != old:
            changed += 1
        return f"{m.group(1)}{loc}{m.group(3)}{new}{m.group(5)}"

    xml2 = re.sub(r"(<loc>)([^<]+)(</loc>\s*<lastmod>)([^<]+)(</lastmod>)", repl, xml)
    SITEMAP.write_text(xml2, encoding="utf-8")

    # sitemap に載っていない公開ページ（canonical が自分以外のページは除く）
    for f in sorted(SITE.glob("*.html")):
        if f.name in seen:
            continue
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', f.read_text(encoding="utf-8"))
        if canon and canon.group(1) not in (BASE + f.name, BASE if f.name == "index.html" else None):
            continue
        print(f"⚠️ sitemap に無いページ: {f.name}")

    dates = re.findall(r"<lastmod>([^<]+)</lastmod>", xml2)
    print(f"{len(dates)}URL・lastmodを{changed}件更新")
    for d in sorted(set(dates), reverse=True):
        print(f"  {d}: {dates.count(d)}件")


if __name__ == "__main__":
    main()
