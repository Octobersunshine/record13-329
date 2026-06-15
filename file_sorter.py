import os
import json
import shutil
import argparse
import time
from pathlib import Path
from collections import defaultdict


DEFAULT_EXTENSION_CATEGORIES = {
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

CONFIG_FILENAME = "file_sorter_config.json"


def load_config(config_path):
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if not isinstance(config, dict):
        raise ValueError("配置文件格式错误: 顶层应为 JSON 对象")
    return config.get("categories", {})


def merge_rules(base_categories, custom_categories):
    merged = {}
    for category, extensions in base_categories.items():
        merged[category] = list(extensions)
    for category, extensions in custom_categories.items():
        if not isinstance(extensions, list):
            raise ValueError(f"分类 '{category}' 的扩展名列表格式错误，应为数组")
        normalized = [ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                      for ext in extensions]
        if category in merged:
            for ext in normalized:
                if ext not in merged[category]:
                    merged[category].append(ext)
        else:
            merged[category] = normalized
    return merged


def build_extension_map(extension_categories):
    ext_map = {}
    for category, extensions in extension_categories.items():
        for ext in extensions:
            ext_map[ext.lower()] = category
    return ext_map


def categorize_file(filepath, extension_map):
    ext = Path(filepath).suffix.lower()
    if not ext:
        return None
    return extension_map.get(ext, "其他")


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


def sort_directory(source_dir, extension_categories, extension_map,
                   move_files=True, dry_run=False, verbose=False):
    if not os.path.isdir(source_dir):
        raise ValueError(f"目录不存在: {source_dir}")

    source_dir = os.path.abspath(source_dir)
    stats = defaultdict(int)

    for entry in os.listdir(source_dir):
        entry_path = os.path.join(source_dir, entry)

        if os.path.isdir(entry_path):
            if entry in extension_categories or entry == "其他":
                continue

        if os.path.isfile(entry_path):
            category = categorize_file(entry_path, extension_map)
            if category is None:
                if verbose:
                    print(f"跳过 (无扩展名): {entry}")
                continue

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


def watch_directory(source_dir, extension_categories, extension_map,
                    interval=2, move_files=True, verbose=False):
    print(f"开始监控目录: {source_dir}")
    print(f"检查间隔: {interval} 秒 (按 Ctrl+C 停止)")
    try:
        while True:
            stats = sort_directory(source_dir, extension_categories, extension_map,
                                   move_files=move_files, dry_run=False, verbose=verbose)
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


def print_categories(extension_categories):
    print("当前分类规则:")
    for category, extensions in extension_categories.items():
        print(f"\n  [{category}]")
        print(f"    {', '.join(extensions)}")
    print("\n  [其他]")
    print("    未匹配到以上任何扩展名的文件")


def init_config(config_path):
    if os.path.exists(config_path):
        raise FileExistsError(f"配置文件已存在: {config_path}")
    template = {
        "categories": {
            "图片": [".heif", ".avif"],
            "文档": [".wps", ".et"],
            "视频": [".rmvb", ".asf"],
            "压缩包": [".zst", ".lz4"],
            "代码": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"],
            "音乐": [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma"]
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"配置模板已生成: {config_path}")
    print("请编辑该文件来自定义分类规则，然后使用 --config 参数指定配置文件路径。")


def resolve_config_path(config_arg):
    if config_arg:
        return os.path.abspath(config_arg)
    cwd_config = os.path.join(os.getcwd(), CONFIG_FILENAME)
    if os.path.isfile(cwd_config):
        return cwd_config
    return None


def build_rules(config_path=None):
    extension_categories = dict(DEFAULT_EXTENSION_CATEGORIES)
    config_source = "默认规则"
    if config_path:
        custom = load_config(config_path)
        if custom:
            extension_categories = merge_rules(DEFAULT_EXTENSION_CATEGORIES, custom)
            config_source = f"默认规则 + 自定义规则 ({config_path})"
    extension_map = build_extension_map(extension_categories)
    return extension_categories, extension_map, config_source


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
    parser.add_argument(
        "--config",
        metavar="FILE",
        help=f"指定自定义规则配置文件 (JSON); 未指定时自动查找当前目录下的 {CONFIG_FILENAME}"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help=f"在当前目录生成模板配置文件 {CONFIG_FILENAME}"
    )

    args = parser.parse_args()

    if args.init_config:
        target = os.path.abspath(args.config) if args.config else os.path.join(os.getcwd(), CONFIG_FILENAME)
        init_config(target)
        return

    config_path = resolve_config_path(args.config)
    extension_categories, extension_map, config_source = build_rules(config_path)

    if args.list_categories:
        print(f"规则来源: {config_source}\n")
        print_categories(extension_categories)
        return

    target_path = os.path.abspath(args.path)

    if args.verbose:
        print(f"规则来源: {config_source}")
        print()

    if args.watch:
        watch_directory(
            target_path, extension_categories, extension_map,
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
            target_path, extension_categories, extension_map,
            move_files=not args.copy,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        print_summary(stats)


if __name__ == "__main__":
    main()
