import os
import shutil
import argparse
import time
from pathlib import Path
from collections import defaultdict


EXTENSION_CATEGORIES = {
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
             ".webp", ".svg", ".ico", ".raw", ".heic", ".psd"],
    "文档": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
             ".txt", ".md", ".csv", ".odt", ".ods", ".odp", ".rtf",
             ".tex", ".epub", ".pages", ".numbers", ".key"],
    "视频": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm",
             ".m4v", ".mpeg", ".mpg", ".3gp", ".ts", ".mts", ".vob"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
              ".tgz", ".tbz2", ".cab", ".iso", ".dmg", ".arc"]
}


def build_extension_map():
    ext_map = {}
    for category, extensions in EXTENSION_CATEGORIES.items():
        for ext in extensions:
            ext_map[ext.lower()] = category
    return ext_map


EXTENSION_MAP = build_extension_map()


def categorize_file(filepath):
    ext = Path(filepath).suffix.lower()
    return EXTENSION_MAP.get(ext, "其他")


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_unique_dest(dest_path):
    if not os.path.exists(dest_path):
        return dest_path
    base, ext = os.path.splitext(dest_path)
    counter = 1
    while True:
        new_path = f"{base}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def sort_directory(source_dir, move_files=True, dry_run=False, verbose=False):
    if not os.path.isdir(source_dir):
        raise ValueError(f"目录不存在: {source_dir}")

    source_dir = os.path.abspath(source_dir)
    stats = defaultdict(int)

    for entry in os.listdir(source_dir):
        entry_path = os.path.join(source_dir, entry)

        if os.path.isdir(entry_path):
            category_dir_name = entry
            if category_dir_name in EXTENSION_CATEGORIES or category_dir_name == "其他":
                continue

        if os.path.isfile(entry_path):
            category = categorize_file(entry_path)
            target_dir = os.path.join(source_dir, category)
            target_path = os.path.join(target_dir, entry)
            target_path = get_unique_dest(target_path)

            if verbose:
                action = "[DRY-RUN] 将移动" if dry_run else "移动" if move_files else "将复制"
                print(f"{action}: {entry} -> {category}/")

            if not dry_run:
                ensure_dir(target_dir)
                if move_files:
                    shutil.move(entry_path, target_path)
                else:
                    shutil.copy2(entry_path, target_path)

            stats[category] += 1

    return dict(stats)


def watch_directory(source_dir, interval=2, move_files=True, verbose=False):
    print(f"开始监控目录: {source_dir}")
    print(f"检查间隔: {interval} 秒 (按 Ctrl+C 停止)")
    try:
        while True:
            stats = sort_directory(source_dir, move_files=move_files,
                                   dry_run=False, verbose=verbose)
            if stats and verbose:
                print(f"本轮处理完成: {dict(stats)}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监控已停止。")


def print_summary(stats):
    total = sum(stats.values())
    print("\n===== 分类统计 =====")
    if total == 0:
        print("没有文件需要分类。")
        return
    for category, count in sorted(stats.items()):
        print(f"  {category}: {count} 个文件")
    print(f"  总计: {total} 个文件")
    print("====================")


def main():
    parser = argparse.ArgumentParser(
        description="文件分类服务 - 按扩展名自动将文件移动到对应文件夹"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="要整理的目录路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="持续监控模式，自动处理新增文件"
    )
    parser.add_argument(
        "-c", "--copy",
        action="store_true",
        help="复制文件而非移动"
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="试运行模式，不实际移动文件"
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=2,
        help="监控模式下的检查间隔秒数 (默认: 2)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细处理信息"
    )
    parser.add_argument(
        "-l", "--list-categories",
        action="store_true",
        help="列出所有支持的分类和扩展名"
    )

    args = parser.parse_args()

    if args.list_categories:
        print("支持的分类和扩展名:")
        for category, extensions in EXTENSION_CATEGORIES.items():
            print(f"\n  [{category}]")
            print(f"    {', '.join(extensions)}")
        print("\n  [其他]")
        print("    未匹配到以上任何扩展名的文件")
        return

    target_path = os.path.abspath(args.path)

    if args.watch:
        watch_directory(
            target_path,
            interval=args.interval,
            move_files=not args.copy,
            verbose=args.verbose
        )
    else:
        print(f"正在整理目录: {target_path}")
        if args.dry_run:
            print("(试运行模式，不会实际改动文件)")
        print()
        stats = sort_directory(
            target_path,
            move_files=not args.copy,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        print_summary(stats)


if __name__ == "__main__":
    main()
