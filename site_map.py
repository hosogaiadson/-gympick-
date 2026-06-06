#!/usr/bin/env python3
"""
GYMPICK サイト全体マップ
68記事を分類・集計して、CVファネルとSEO構造を可視化
"""

import re
from pathlib import Path
from collections import defaultdict

SITE_DIR = Path(__file__).parent

# 駅名と目的キーワード
STATIONS = ['umeda', 'kitahama', 'fukushima', 'esaka', 'toyonaka', 'takatsuki',
            'temmabashi', 'minamimorimachi']
PURPOSES = ['after-work', 'wedding', 'postpartum', 'effect', 'cost',
            'pay-per-use', 'women', 'ladys-wedding']

# 固定ページ
FIXED_PAGES = ['index', 'about', 'contact', 'privacy', 'sitemap', 'ladys',
               'fis-osaka', 'category-osaka']

# PPC型LP化済み
PPC_LP_DONE = ['wedding', 'postpartum', 'after-work', 'umeda-after-work', 'effect']


def classify(filename):
    name = filename.replace('.html', '')

    # 固定ページ
    if name in FIXED_PAGES:
        return ('固定', name, '')

    # 駅×目的
    for station in STATIONS:
        if name.startswith(station + '-'):
            rest = name[len(station) + 1:]
            return ('駅×目的', station, rest)

    # 単一目的の主要記事
    if name in ['after-work', 'wedding', 'postpartum', 'effect', 'cost',
                'pay-per-use', 'women']:
        return ('Sランク主要', name, '')

    # その他の派生記事
    return ('派生記事', name, '')


def analyze_file(filepath):
    """記事1つの中身を分析"""
    try:
        html = filepath.read_text(encoding='utf-8')
    except:
        return None

    # タイトル
    title_m = re.search(r'<title>([^<]+)</title>', html)
    title = title_m.group(1) if title_m else ''

    # H1
    h1_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    h1 = h1_m.group(1) if h1_m else ''

    # 文字数
    text_only = re.sub(r'<[^>]+>', '', html)
    char_count = len(re.sub(r'\s+', '', text_only))

    # アフィリンク数（成果発生点）
    affiliate_count = len(re.findall(r'href="https://af\.moshimo\.com', html)) + \
                      len(re.findall(r'href="https://px\.a8\.net', html))

    # CTA数（ボタンclass）
    cta_count = len(re.findall(r'class="cta-btn"', html)) + \
                len(re.findall(r'class="lp-cta-(?:main|light)"', html))

    # 内部リンク数
    internal_links = len(re.findall(r'href="([a-z][a-z0-9-]*\.html)"', html))

    # PPC型LP判定
    is_ppc_lp = 'lp.css' in html and 'lp-hero' in html

    return {
        'title': title,
        'h1': h1,
        'chars': char_count,
        'affiliate': affiliate_count,
        'cta': cta_count,
        'internal_links': internal_links,
        'is_ppc_lp': is_ppc_lp,
    }


def main():
    files = sorted(SITE_DIR.glob('*.html'))

    # 分類して集計
    by_category = defaultdict(list)

    for f in files:
        category, station, purpose = classify(f.name)
        data = analyze_file(f)
        if data is None:
            continue
        data['filename'] = f.name
        data['station'] = station
        data['purpose'] = purpose
        by_category[category].append(data)

    # 出力
    print('=' * 90)
    print('GYMPICK サイト全体マップ')
    print('=' * 90)
    print(f'\n📊 全{sum(len(v) for v in by_category.values())}記事')
    print()

    # カテゴリ別サマリー
    print('■ カテゴリ別件数')
    print('-' * 90)
    for cat, items in by_category.items():
        ppc = sum(1 for x in items if x['is_ppc_lp'])
        total_aff = sum(x['affiliate'] for x in items)
        total_cta = sum(x['cta'] for x in items)
        print(f'{cat:<12} {len(items):>3}記事  PPC化:{ppc:>2}  アフィリンク総数:{total_aff:>3}  CTA総数:{total_cta:>3}')
    print()

    # 駅×目的マトリクス
    print('■ 駅×目的マトリクス（駅×目的の42本）')
    print('-' * 90)
    matrix = defaultdict(dict)
    for item in by_category['駅×目的']:
        matrix[item['station']][item['purpose']] = item

    print(f'{"駅":<14}', end='')
    purposes_list = ['after-work', 'wedding', 'cost', 'effect', 'pay-per-use', 'women',
                     'ladys-wedding', 'ladys-postpartum', 'ladys-women']
    for p in purposes_list:
        print(f'{p[:9]:>10}', end='')
    print()
    for station in STATIONS:
        if station in matrix:
            print(f'{station:<14}', end='')
            for p in purposes_list:
                if p in matrix[station]:
                    d = matrix[station][p]
                    mark = '⭐' if d['is_ppc_lp'] else '○'
                    print(f'{mark:>10}', end='')
                else:
                    print(f'{"-":>10}', end='')
            print()
    print()

    # Sランク主要記事の詳細
    print('■ Sランク主要記事（PPC化候補）')
    print('-' * 90)
    print(f'{"ファイル":<22}{"PPC":^6}{"文字":>7}{"CTA":>5}{"アフィ":>7}{"内部":>5}  タイトル')
    for item in sorted(by_category['Sランク主要'], key=lambda x: x['filename']):
        ppc = '⭐' if item['is_ppc_lp'] else '-'
        title_short = item['title'][:35]
        print(f'{item["filename"]:<22}{ppc:^6}{item["chars"]:>7}{item["cta"]:>5}{item["affiliate"]:>7}{item["internal_links"]:>5}  {title_short}')
    print()

    # 派生記事
    print('■ 派生記事（SEO情報記事）')
    print('-' * 90)
    print(f'{"ファイル":<28}{"文字":>7}{"CTA":>5}{"アフィ":>7}  タイトル')
    for item in sorted(by_category['派生記事'], key=lambda x: x['filename']):
        title_short = item['title'][:35]
        print(f'{item["filename"]:<28}{item["chars"]:>7}{item["cta"]:>5}{item["affiliate"]:>7}  {title_short}')
    print()

    # 改善ポイント
    print('■ 改善ポイント分析')
    print('-' * 90)

    # CTA数が少ない記事（離脱しやすい）
    low_cta = [x for x in (by_category['駅×目的'] + by_category['Sランク主要'] + by_category['派生記事'])
               if x['cta'] < 2 and not x['is_ppc_lp']]
    print(f'⚠️ CTA2個未満の記事: {len(low_cta)}件 → CV取りこぼし')

    # アフィリンクゼロの記事
    no_aff = [x for x in (by_category['駅×目的'] + by_category['Sランク主要'] + by_category['派生記事'])
              if x['affiliate'] == 0]
    print(f'⚠️ アフィリンクゼロ記事: {len(no_aff)}件 → 収益化されてない')
    if no_aff:
        for x in no_aff[:5]:
            print(f'   - {x["filename"]}: {x["title"][:40]}')

    # 駅×目的のPPC化候補
    not_ppc = [x for x in by_category['駅×目的'] if not x['is_ppc_lp']]
    print(f'📌 駅×目的でPPC化されてない: {len(not_ppc)}件')

    print()
    print('=' * 90)


if __name__ == '__main__':
    main()
