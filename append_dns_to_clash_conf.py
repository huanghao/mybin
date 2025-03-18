import argparse
from pathlib import Path
import shutil
import re


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="向Clash配置文件添加DNS服务器")
    parser.add_argument(
        "-i",
        "--inplace",
        action="store_true",
        help="直接修改原文件（会自动创建.bak备份），默认只显示结果",
    )
    parser.add_argument(
        "--dns", default="11.11.11.11", help="要添加的DNS服务器地址，默认为11.11.11.11"
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="/Users/huanghao/.config/clash/OpenConnectUs.yaml",
        help="要处理的配置文件路径",
    )
    return parser.parse_args()


def update_dns_line(line: str, dns: str) -> str:
    """更新包含DNS列表的行

    Args:
        line: 原始行内容
        dns: 要添加的DNS服务器

    Returns:
        更新后的行内容
    """
    # 提取现有的DNS列表
    match = re.match(r"^(\s+(?:default-nameserver|nameserver):\s*\[)(.*?)(\].*)$", line)
    if not match:
        return line

    prefix, dns_list, suffix = match.groups()

    # 解析现有DNS列表
    dns_entries = [entry.strip() for entry in dns_list.split(",") if entry.strip()]

    # 如果新DNS不在列表中，添加到最前面
    if dns not in dns_entries:
        dns_entries.insert(0, dns)

    # 重新组装行，保持原有格式
    return f"{prefix}{', '.join(dns_entries)}{suffix}"


def backup_file(file_path: Path) -> Path:
    """创建文件备份"""
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy2(file_path, backup_path)
    return backup_path


def process_file(content: str, dns: str) -> str:
    """处理文件内容

    Args:
        content: 文件内容
        dns: 要添加的DNS服务器

    Returns:
        处理后的文件内容和是否有修改的标志
    """
    lines = content.splitlines()
    in_dns_section = False
    result = []
    modified = False
    modified_lines = []

    for i, line in enumerate(lines):
        if line.startswith("dns:"):
            in_dns_section = True
        elif in_dns_section and (not line.startswith(" ") or line.startswith("---")):
            in_dns_section = False

        new_line = line
        if in_dns_section and ("default-nameserver:" in line or "nameserver:" in line):
            new_line = update_dns_line(line, dns)
            if new_line != line:
                modified = True
                modified_lines.append((i + 1, line, new_line))

        result.append(new_line)

    return "\n".join(result), modified, modified_lines


def main():
    """主函数"""
    args = parse_args()
    file_path = Path(args.file)

    # 读取文件内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 处理内容
    new_content, modified, modified_lines = process_file(content, args.dns)

    if not modified:
        print(f"ℹ️ DNS {args.dns} 已经存在于配置中，无需修改")
        return

    # 显示修改内容
    print("\n变更内容:")
    for line_num, old_line, new_line in modified_lines:
        print(f"第 {line_num} 行:")
        print(f"- {old_line}")
        print(f"+ {new_line}\n")

    if args.inplace:
        # 创建备份
        backup_path = backup_file(file_path)
        # 写入更新后的内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ DNS {args.dns} 已添加到配置文件")
        print(f"原文件已备份: {backup_path}")
        print(f"原文件已更新: {file_path}")
    else:
        print(f"\n# 提示: 使用 -i 选项可以直接修改原文件 {file_path}")


if __name__ == "__main__":
    main()
