#!/usr/bin/env python3
"""Merge upstream IPTV sources from a2256569/tv into one tv.txt file.

Only these 7 upstream files are merged - no sample/template file
(e.g. the GT9527 tv.txt shown earlier was format reference only,
its channels are NOT merged in):
  LNYDQWT.txt, SXG, ZB.txt, iTV.txt, lnlt.txt, sdzb.txt, tv.m3u

Output format (same as GT9527/mytv tv.txt):
  <来源-分组名>,#genre#
  <频道名>,<播放地址>
  ...

Grouping rule: the group name is prefixed with the source name,
so same-named groups from different files stay separate, e.g.
  LNYDQWT-4K频道,#genre#
  SXG-央视频道,#genre#
  ZB-东北地区,#genre#
  iTV-4K频道,#genre#
  lnlt-4K频道,#genre#
  sdzb-河南酒店源,#genre#
  tv-央视,#genre#

- .txt / no-extension files are already in that format.
- tv.m3u (#EXTINF + group-title) is converted to the same format.
- Exact duplicate (频道名, 播放地址) pairs are kept only once
  *within the same prefixed group* - the same channel may appear
  under LNYDQWT-4K频道 and under iTV-4K频道, because they come
  from different sources.
- Groups are separated by one blank line in the output file.
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
        add(groups, order, seen, group, name, url)

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
                add(groups, order, seen, group, name, url)
            i = j + 1
            continue
        i += 1

def add(groups, order, seen, group, name, url):
    key = (group, name, url)
    if key in seen:
        return
    seen.add(key)
    if group not in groups:
        groups[group] = []
        order.append(group)
    groups[group].append((name, url))

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "tv.txt"
    groups = {}
    order = []
    seen = set()
    stats = {}
    for name in SOURCES:
        text = fetch(name)
        before = len(seen)
        if name.endswith(".m3u"):
            parse_m3u(text, groups, order, seen, PREFIX[name])
        else:
            parse_txt(text, groups, order, seen, PREFIX[name])
        stats[name] = len(seen) - before
        print(f"{name}: +{stats[name]} unique channels", file=sys.stderr)

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
            for name, url in channels:
                f.write(f"{name},{url}\n")

    total = sum(len(v) for v in groups.values())
    print(f"groups={len(order)} channels={total} -> {out}", file=sys.stderr)

if __name__ == "__main__":
    main()
