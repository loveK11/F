# TV 直播源自动合并同步

上游：`a2256569/tv`
目标：`loveK11/F`，输出到 `live` 分支的 `tv.txt`

## 包含的文件

- `.github/workflows/sync-tv.yml` — GitHub Actions 定时任务
- `scripts/merge_tv.py` — 合并脚本
- `tv.txt` — 用今天（2026-11-25）的上游文件本地跑出来的合并示例

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

分组规则：只给每个源文件的**第一个分组**加来源前缀，后面的分组保持原名，例如：

```
LNYDQWT-4K频道,#genre#
...
<空一行>
央视频道,#genre#          <- LNYDQWT 的第二个分组，不加前缀
...
<空一行>
SXG-央视频道,#genre#      <- SXG 的第一个分组，加前缀
...
<空一行>
卫视频道,#genre#          <- SXG 的第二个分组，不加前缀
```

前缀是去掉后缀的文件名：LNYDQWT、SXG、ZB、iTV、lnlt、sdzb、tv。
不带前缀的同名分组会合并到同一个分组下，按首次出现顺序排。

- 组与组之间空一行，文件开头和结尾不留多余空行
- 同一个最终分组里，完全相同的（频道名，地址）只保留一次
- 默认跳过 `iTV.txt` 里的成人分组 `🔞成人9+9⁺_0000`（这个分组有 586 条），想收录就把 `scripts/merge_tv.py` 里 `EXCLUDE_GROUPS` 那一行删掉

今天实测结果：45 个分组，7050 个频道，共 7139 行（含 44 个组间隔空行）。

## 怎么放到你的仓库

这两个文件都要放在 `main` 分支上（定时任务只从默认分支运行）：

1. 打开 https://github.com/loveK11/F ，确保在 `main` 分支
2. 点 `Add file` → `Create new file`，文件名填 `scripts/merge_tv.py`，粘贴本包里同名文件的内容，提交
3. 再同样新建 `.github/workflows/sync-tv.yml`，粘贴本包里同名文件的内容，提交
4. 去仓库的 `Actions` 标签页，如果提示要开启 Actions 就点启用
5. 在左侧找到 `Sync TV`，点 `Run workflow` 手动跑一次，第一次就会自动创建 `live` 分支并生成 `tv.txt`

之后每天北京时间 10:00 自动跑一次（`cron: '0 2 * * *'`）。上游没变就不提交，上游变了就自动更新 `live` 分支。

想改频率就改 `sync-tv.yml` 里的 cron，例如每 6 小时一次改成 `'0 */6 * * *'`。

完成后你的合并源地址就是：

```
https://raw.githubusercontent.com/loveK11/F/live/tv.txt
```

## 本地自己跑（可选）

```bash
python3 scripts/merge_tv.py tv.txt
```
