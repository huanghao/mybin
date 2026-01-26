import argparse
from pathlib import Path
import shutil
import re


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="修改Clash配置文件")
    parser.add_argument(
        "-i",
        "--inplace",
        action="store_true",
        help="直接修改原文件（会自动创建.bak备份），默认只显示结果",
    )
    parser.add_argument(
        "--dns", 
        default="11.11.11.11", 
        help="要添加的DNS服务器地址，例如 11.11.11.11"
    )
    parser.add_argument(
        "--rule",
        default="DOMAIN-SUFFIX,sankuai.com,DIRECT",
        help="要添加的规则，格式为'类型,内容,策略'，例如 'DOMAIN-SUFFIX,example.com,DIRECT'"
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


def process_file(content: str, dns: str = None, rule: str = None):
    """处理文件内容

    Args:
        content: 文件内容
        dns: 要添加的DNS服务器
        rule: 要添加的规则

    Returns:
        处理后的文件内容和是否有修改的标志
    """
    lines = content.splitlines()
    result = []
    
    # 状态跟踪
    in_dns_section = False
    in_rules_section = False
    
    # 修改跟踪
    dns_modified = False
    rule_modified = False
    rule_exists = False
    meituan_found = False
    modified_lines = []

    # 提取规则信息
    rule_type = ""
    rule_domain = ""
    if rule:
        # 规则格式例如: 'DOMAIN-SUFFIX,example.com,DIRECT'
        parts = rule.split(',')
        if len(parts) >= 2:
            rule_type = parts[0]
            rule_domain = parts[1]
    
    for i, line in enumerate(lines):
        current_line = line
        
        # DNS部分处理
        if dns:
            if line.startswith("dns:"):
                in_dns_section = True
            elif in_dns_section and (not line.startswith(" ") or line.startswith("---")):
                in_dns_section = False
            
            if in_dns_section and ("default-nameserver:" in line or "nameserver:" in line):
                new_line = update_dns_line(line, dns)
                if new_line != line:
                    current_line = new_line
                    dns_modified = True
                    modified_lines.append((i + 1, line, new_line))
        
        # 规则部分处理
        if rule:
            if line.startswith("rules:"):
                in_rules_section = True
            elif in_rules_section and (not line.startswith(" ") or line.startswith("---")):
                in_rules_section = False
            
            if in_rules_section:
                # 检查是否已存在相同的规则
                if rule_type and rule_domain and f"{rule_type},{rule_domain}" in line:
                    rule_exists = True
                
                # 检查是否遇到了meituan.com规则
                if 'meituan.com' in line and 'DOMAIN-SUFFIX' in line and not rule_exists and not rule_modified and not meituan_found:
                    meituan_found = True
                    # 在meituan.com规则前添加sankuai.com规则
                    rule_line = f"    - '{rule}'"
                    result.append(rule_line)
                    rule_modified = True
                    modified_lines.append((i + 1, "", rule_line))
        
        # 添加当前行到结果
        result.append(current_line)
    
    # 记录修改状态
    modified = dns_modified or rule_modified
    
    # 收集修改信息
    modification_info = {
        "dns_modified": dns_modified,
        "rule_modified": rule_modified,
        "rule_exists": rule_exists,
        "meituan_found": meituan_found
    }

    return "\n".join(result), modified, modified_lines, modification_info


def main():
    """主函数"""
    args = parse_args()
    file_path = Path(args.file)
    print(args.file)

    # 读取文件内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 处理内容
    new_content, modified, modified_lines, mod_info = process_file(content, args.dns, args.rule)

    if not modified:
        messages = []
        if args.dns:
            messages.append(f"DNS {args.dns} 已经存在于配置中")
        
        if args.rule:
            if mod_info["rule_exists"]:
                messages.append(f"规则 {args.rule} 已经存在于配置中")
            elif not mod_info["meituan_found"]:
                messages.append(f"未找到meituan.com规则，无法添加 {args.rule}")
        
        print(f"ℹ️ {' 和 '.join(messages)}，无需修改")
        return

    # 显示修改内容
    print("\n变更内容:")
    for line_num, old_line, new_line in modified_lines:
        print(f"第 {line_num} 行:")
        if old_line:
            print(f"- {old_line}")
        print(f"+ {new_line}\n")

    if args.inplace:
        # 创建备份
        backup_path = backup_file(file_path)
        # 写入更新后的内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        actions = []
        if mod_info["dns_modified"]:
            actions.append(f"DNS {args.dns} 已添加")
        if mod_info["rule_modified"]:
            actions.append(f"规则 {args.rule} 已添加到meituan.com前面")
        
        print(f"✅ {' 和 '.join(actions)}到配置文件")
        print(f"原文件已备份: {backup_path}")
        print(f"原文件已更新: {file_path}")
    else:
        print(f"\n# 提示: 使用 -i 选项可以直接修改原文件 {file_path}")


if __name__ == "__main__":
    main()
