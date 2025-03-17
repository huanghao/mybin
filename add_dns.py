import yaml
import argparse
import shutil
import sys
from pathlib import Path

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='向Clash配置文件添加DNS服务器')
    parser.add_argument('-i', '--inplace', 
                       action='store_true',
                       help='直接修改原文件（会自动创建.bak备份），默认只显示结果')
    parser.add_argument('--dns',
                       default="11.11.11.11",
                       help='要添加的DNS服务器地址，默认为11.11.11.11')
    parser.add_argument('file',
                       nargs='?',
                       default="/Users/huanghao/.config/clash/OpenConnectUs.yaml",
                       help='要处理的配置文件路径')
    return parser.parse_args()

def update_dns_config(config, new_dns):
    """更新DNS配置
    
    Args:
        config: YAML配置字典
        new_dns: 要添加的DNS服务器地址
    """
    # 确保 `dns` 字段存在
    if "dns" not in config:
        config["dns"] = {}

    # 处理 `default-nameserver`
    if "default-nameserver" not in config["dns"]:
        config["dns"]["default-nameserver"] = []
    if new_dns not in config["dns"]["default-nameserver"]:
        config["dns"]["default-nameserver"].append(new_dns)

    # 处理 `nameserver`
    if "nameserver" not in config["dns"]:
        config["dns"]["nameserver"] = []
    if new_dns not in config["dns"]["nameserver"]:
        config["dns"]["nameserver"].append(new_dns)

def backup_file(file_path: Path) -> Path:
    """创建文件备份
    
    Args:
        file_path: 要备份的文件路径
        
    Returns:
        备份文件的路径
    """
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    shutil.copy2(file_path, backup_path)
    return backup_path

def main():
    """主函数"""
    args = parse_args()
    file_path = Path(args.file)
    
    # 读取YAML文件
    with open(file_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    
    # 更新DNS配置
    update_dns_config(config, args.dns)
    
    if args.inplace:
        # 创建备份
        backup_path = backup_file(file_path)
        # 直接修改原文件
        output_path = file_path
        # 写入配置到文件
        with open(output_path, "w", encoding="utf-8") as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
        print(f"✅ DNS {args.dns} 已添加到配置文件")
        print(f"原文件已备份: {backup_path}")
        print(f"原文件已更新: {output_path}")
    else:
        # 直接输出到屏幕
        print("# 更新后的配置:")
        print("---")
        yaml.dump(config, sys.stdout, default_flow_style=False, allow_unicode=True)
        print(f"\n# 提示: 使用 -i 选项可以直接修改原文件 {file_path}")

if __name__ == "__main__":
    main()