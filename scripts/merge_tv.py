#!/usr/bin/env python3
"""Merge upstream IPTV sources from a2256569/tv into tv.txt + tv.m3u.

Only these 7 upstream files are merged - no sample/template file
(e.g. the GT9527 tv.txt shown earlier was format reference only,
its channels are NOT merged in):
  LNYDQWT.txt, SXG, ZB.txt, iTV.txt, lnlt.txt, sdzb.txt, tv.m3u

Why every group gets a source prefix (fixed 2026-11-25):
  Prefixing only the first group of each file merged the other
  groups into one plain heading, e.g. SXG's 卫视频道, ZB's
  央视频道/卫视频道 and lnlt's 央视频道/卫视频道/省内频道/
  晴彩频道/CHC电影频道 all landed in the plain 卫视频道 /
  央视频道 / ... groups. They were technically in the file,
  but not findable as SXG/ZB/lnlt groups. Worse, dedup was
  then per plain group, so iTV's groups (whose URLs are the
  same as LNYDQWT's) were dropped as duplicates and iTV
  contributed only 38 channels. Prefixing every group keeps
  each source's groups separate and dedup is then only
  within the same prefixed group.

Grouping rule (every group prefixed):
  LNYDQWT-4K频道,#genre#
  LNYDQWT-央视频道,#genre#
  SXG-央视频道,#genre#
  SXG-卫视频道,#genre#
  ZB-东北地区,#genre#
  ZB-央视频道,#genre#
  ZB-卫视频道,#genre#
  iTV-4K频道,#genre#
  lnlt-央视频道,#genre#
  lnlt-卫视频道,#genre#
  lnlt-省内频道,#genre#
  lnlt-晴彩频道,#genre#
  lnlt-CHC电影频道,#genre#
  tv-央视,#genre#

- .txt / no-extension files are already in that format.
- tv.m3u (#EXTINF + group-title) is converted to the same format.
- Exact duplicate (频道名, 播放地址) pairs are kept only once
  *within the same prefixed group* - the same channel may appear
  under LNYDQWT-4K频道 and under iTV-4K频道, because they come
  from different sources.
- Groups are separated by one blank line in the txt output.

user-agent for Huya / Douyu / tv.m3u channels:
  These streams need User-Agent "qqlive" to play, otherwise
  they are rejected. The header the user gave:
    "header": {"User-Agent": "qqlive"}
  is the #EXTHTTP JSON form, so the m3u output writes BOTH
  standard forms for those channels, between #EXTINF and URL:
    #EXTVLCOPT:http-user-agent=qqlive
    #EXTHTTP:{"User-Agent":"qqlive"}
  #EXTVLCOPT is the VLC / iptv-org standard, #EXTHTTP is
  the TVBox / TiviMate / Kodi JSON-header form. Players
  ignore the tag they do not understand, so writing both
  covers both families. The txt format has no header field,
  so there the URL gets the Kodi-style inline suffix:
    频道名,地址|User-Agent=qqlive
  Other channels get no UA line/suffix.
  UA is needed for: every channel from tv.m3u (224), plus
  sdzb's 斗鱼💖主播 (198), 虎牙💖主播 (342) and 瑜伽💖矫正 (21)
  — 785 channels in total.
  Usage: python3 scripts/merge_tv.py tv.txt [tv.m3u]
"""
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/a2256569/tv/main/"

SOURCES = [
    "LNYDQWT.txt",
    "SXG",
    "ZB.txt",
    "iTV.txt",
    "lnlt.txt",
    "sdzb.txt",
    "tv.m3u",
]

# Source file -> group prefix (extension stripped).
PREFIX = {
    "LNYDQWT.txt": "LNYDQWT",
    "SXG": "SXG",
    "ZB.txt": "ZB",
    "iTV.txt": "iTV",
    "lnlt.txt": "lnlt",
    "sdzb.txt": "sdzb",
    "tv.m3u": "tv",
}

# Exact group names (before prefixing) to skip. Delete the entry to include it.
# The adult group "🔞成人9+9⁺_0000" found in iTV.txt is excluded by default.
EXCLUDE_GROUPS = {"🔞成人9+9⁺_0000"}

# User-Agent required by Huya / Douyu / tv.m3u streams.
USER_AGENT = "qqlive"

# Prefixed groups (from sdzb.txt) that need the UA above.
# tv.m3u channels need it too, regardless of group.
UA_GROUPS = {"sdzb-斗鱼💖主播", "sdzb-虎牙💖主播", "sdzb-瑜伽💖矫正"}

GROUP_RE = re.compile(r'group-title="([^"]*)"')

def prefixed(prefix, group):
    return f"{prefix}-{group}"

def fetch(name):
    url = BASE + name
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_txt(text, groups, order, seen, prefix):
    group_orig = "其他"
    group = prefixed(prefix, group_orig)
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith(",#genre#"):
            group_orig = line.rsplit(",", 1)[0].strip() or "其他"
            group = prefixed(prefix, group_orig)
            if group not in groups:
                groups[group] = []
                order.append(group)
            continue
        if "," not in line:
            continue
        name, url = line.split(",", 1)
        name, url = name.strip(), url.strip()
        if not name or not url or not url.startswith(("http://", "https://", "rtp://")):
            continue
        if group_orig in EXCLUDE_GROUPS:
            continue
        add(groups, order, seen, group, name, url, needs_ua=group in UA_GROUPS)

def parse_m3u(text, groups, order, seen, prefix):
    lines = [l.strip() for l in text.splitlines()]
    i = 0
    group_orig = "其他"
    group = prefixed(prefix, group_orig)
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            m = GROUP_RE.search(line)
            if m and m.group(1).strip():
                group_orig = m.group(1).strip()
                group = prefixed(prefix, group_orig)
            # Name is after the last comma on the #EXTINF line.
            name = line.rsplit(",", 1)[-1].strip() if "," in line else ""
            # The next non-empty, non-# line is the URL.
            j = i + 1
            url = ""
            while j < len(lines):
                if lines[j] and not lines[j].startswith("#"):
                    url = lines[j]
                    break
                j += 1
            if name and url and group_orig not in EXCLUDE_GROUPS:
                add(groups, order, seen, group, name, url, needs_ua=True)
            i = j + 1
            continue
        i += 1

def add(groups, order, seen, group, name, url, needs_ua=False):
    key = (group, name, url)
    if key in seen:
        return
    seen.add(key)
    if group not in groups:
        groups[group] = []
        order.append(group)
    groups[group].append((name, url, needs_ua))

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "tv.txt"
    out_m3u = sys.argv[2] if len(sys.argv) > 2 else None
    groups = {}
    order = []
    seen = set()
    for name in SOURCES:
        text = fetch(name)
        before = len(seen)
        if name.endswith(".m3u"):
            parse_m3u(text, groups, order, seen, PREFIX[name])
        else:
            parse_txt(text, groups, order, seen, PREFIX[name])
        print(f"{name}: +{len(seen) - before} unique channels", file=sys.stderr)

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        first = True
        for group in order:
            channels = groups[group]
            if not channels:
                continue
            if not first:
                f.write("\n")
            first = False
            f.write(f"{group},#genre#\n")
            for name, url, needs_ua in channels:
                if needs_ua:
                    f.write(f"{name},{url}|User-Agent={USER_AGENT}\n")
                else:
                    f.write(f"{name},{url}\n")

    total = sum(len(v) for v in groups.values())
    ua_total = sum(1 for v in groups.values() for _, _, u in v if u)
    print(f"groups={len(order)} channels={total} ua_channels={ua_total} -> {out}", file=sys.stderr)

    if out_m3u:
        with open(out_m3u, "w", encoding="utf-8", newline="\n") as f:
            f.write("#EXTM3U\n")
            for group in order:
                channels = groups[group]
                if not channels:
                    continue
                for name, url, needs_ua in channels:
                    f.write(f'#EXTINF:-1 group-title="{group}",{name}\n')
                    if needs_ua:
                        f.write(f"#EXTVLCOPT:http-user-agent={USER_AGENT}\n")
                        f.write(f'#EXTHTTP:{{"User-Agent":"{USER_AGENT}"}}\n')
                    f.write(f"{url}\n")
        print(f"groups={len(order)} channels={total} ua_channels={ua_total} -> {out_m3u}", file=sys.stderr)

if __name__ == "__main__":
    main()
