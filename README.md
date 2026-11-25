# TV 直播源自动合并同步

上游：`a2256569/tv`
目标：`loveK11/F`，输出到 `live` 分支的 `tv.txt` 和 `tv.m3u`

## 包含的文件

- `.github/workflows/sync-tv.yml` — GitHub Actions 定时任务
- `scripts/merge_tv.py` — 合并脚本
- `tv.txt` — 用今天（2026-11-25）的上游文件本地跑出来的合并示例
- `tv.m3u` — 同一份合并的 M3U 版，tv.m3u 来源的频道带 user-agent

## 合并规则

只合并上游仓库的这 7 个文件，样板文件（之前看的 GT9527 tv.txt）只做格式参考，它的频道不合并进来：

| 上游文件 | 格式 |
| --- | --- |
| LNYDQWT.txt | `频道名,地址`，分组 `xxx,#genre#`，原样取 |
| SXG | 同上，无后缀 |
| ZB.txt | 同上 |
| iTV.txt | 同上 |
| lnlt.txt | 同上 |
| sdzb.txt | 同上 |
| tv.m3u | `#EXTINF` + `group-title` 转成 `频道名,地址` |

分组规则：**每个分组都加来源前缀**，各来源的同名分组分开，例如：

```
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
```

前缀是去掉后缀的文件名：LNYDQWT、SXG、ZB、iTV、lnlt、sdzb、tv。

为什么不能只给第一个分组加前缀：2026-11-25 试过一次，只给每文件第一个分组加前缀，其他分组合并到同一个不带前缀的分组下，结果 SXG-卫视频道、ZB-央视频道、ZB-卫视频道、lnlt-央视频道/卫视频道/省内/晴彩/CHC 这些分组在文件里找不到了；而且去重按不带前缀的分组算，iTV 的频道地址和 LNYDQWT 相同就被当成重复删掉，iTV 只剩 38 条。改回全部加前缀后，iTV 恢复到 320 条。

- 组与组之间空一行，文件开头和结尾不留多余空行
- 同一个带前缀的分组里，完全相同的（频道名，地址）只保留一次
- 默认跳过 `iTV.txt` 里的成人分组 `🔞成人9+9⁺_0000`（这个分组有 586 条），想收录就把 `scripts/merge_tv.py` 里 `EXCLUDE_GROUPS` 那一行删掉

今天实测结果：60 个分组，7332 个频道，tv.txt 共 7451 行（含 59 个组间隔空行）。

## user-agent（虎牙、斗鱼、tv.m3u 来源）

这三类源需要 User-Agent `qqlive` 才能播，否则会被服务器拒绝。你给的这个就是标准写法：

```json
"header": {
    "User-Agent": "qqlive"
}
```

txt 格式本身没有放 header 的地方，m3u 有两种标准写法，所以两个文件都按各自的写法加，只加在这三类频道上，共 785 条：tv.m3u 来源的全部 224 条，sdzb 的斗鱼💖主播 198 条、虎牙💖主播 342 条、瑜伽💖矫正 21 条。其他频道不加。

- `tv.m3u` 里，每条在 `#EXTINF` 和地址之间加两行，两种写法都写，播放器认哪种用哪种，不认的会忽略：
  ```
  #EXTINF:-1 group-title="sdzb-虎牙💖主播",【虎牙】xxx
  #EXTVLCOPT:http-user-agent=qqlive
  #EXTHTTP:{"User-Agent":"qqlive"}
  http://81.69.15.31:35455/huya/xxx
  ```
  `#EXTVLCOPT` 是 VLC / iptv-org 的标准写法，`#EXTHTTP` 就是你给的那个 JSON header 的写法，是 TVBox / TiviMate / Kodi 认的。
- `tv.txt` 里，每条地址后面加 `|User-Agent=qqlive`（Kodi 风格的内联写法）：
  ```
  【虎牙】xxx,http://81.69.15.31:35455/huya/xxx|User-Agent=qqlive
  【斗鱼】xxx,http://81.69.15.31:35455/douyu/xxx|User-Agent=qqlive
  CCTV1综合,https://mursor.ottiptv.cc/...|User-Agent=qqlive
  ```

怎么用：优先用 `tv.m3u`，它对播放器的兼容性最好；如果你的播放器只支持 txt，就用 `tv.txt`，支持 `|` 后缀的播放器（TVBox、Kodi 系）能读到这个 UA。如果某个播放器两种都不认，就在播放器设置里手动把全局 User-Agent 设成 `qqlive`，或者换一个支持 `#EXTHTTP` 的播放器（TVBox、TiviMate、VLC）。

## 怎么放到你的仓库

这两个文件都要放在 `main` 分支上（定时任务只从默认分支运行）：

1. 打开 https://github.com/loveK11/F ，确保在 `main` 分支
2. 点 `Add file` → `Create new file`，文件名填 `scripts/merge_tv.py`，粘贴本包里同名文件的内容，提交
3. 再同样新建 `.github/workflows/sync-tv.yml`，粘贴本包里同名文件的内容，提交
4. 去仓库的 `Actions` 标签页，如果提示要开启 Actions 就点启用
5. 在左侧找到 `Sync TV`，点 `Run workflow` 手动跑一次，第一次就会自动创建 `live` 分支并生成 `tv.txt` 和 `tv.m3u`

之后每天北京时间 10:00 自动跑一次（`cron: '0 2 * * *'`）。上游没变就不提交，上游变了就自动更新 `live` 分支。

想改频率就改 `sync-tv.yml` 里的 cron，例如每 6 小时一次改成 `'0 */6 * * *'`。

完成后你的合并源地址就是：

```
https://raw.githubusercontent.com/loveK11/F/live/tv.txt
https://raw.githubusercontent.com/loveK11/F/live/tv.m3u
```

## 本地自己跑（可选）

```bash
python3 scripts/merge_tv.py tv.txt tv.m3u
```
