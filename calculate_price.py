import re
import requests
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def get_rub_to_cny_rate():
    """
    获取卢布兑人民币汇率（100 RUB = X CNY）
    优先从多个数据源抓取实时数据，失败则使用本地缓存
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }
    
    def try_sina():
        try:
            url = "https://hq.sinajs.cn/list=fx_srub"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'gbk'
            data_str = resp.text
            match = re.search(r'"([^"]+)"', data_str)
            if match:
                parts = match.group(1).split(',')
                if len(parts) >= 2:
                    rate_per_100rub = float(parts[1])
                    if rate_per_100rub > 0:
                        print(f"[OK] 汇率已更新: 100 卢布 = {rate_per_100rub:.2f} 人民币 (数据源: 新浪外汇)")
                        return rate_per_100rub / 100.0
        except Exception:
            pass
        return None
    
    def try_frankfurter():
        try:
            url = "https://api.frankfurter.app/latest?from=RUB&to=CNY"
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            rate = data.get('rates', {}).get('CNY')
            if rate and rate > 0:
                print(f"[OK] 汇率已更新: 100 卢布 = {rate*100:.2f} 人民币 (数据源: Frankfurter)")
                return rate
        except Exception:
            pass
        return None
    
    def try_exchange_rate_api():
        try:
            url = "https://api.exchangerate-api.com/v4/latest/CNY"
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            rub_rate = data.get('rates', {}).get('RUB')
            if rub_rate and rub_rate > 0:
                rate = 1 / rub_rate
                print(f"[OK] 汇率已更新: 100 卢布 = {rate*100:.2f} 人民币 (数据源: ExchangeRate-API)")
                return rate
        except Exception:
            pass
        return None
    
    for source_func in [try_sina, try_frankfurter, try_exchange_rate_api]:
        result = source_func()
        if result:
            return result
    
    cached_rate = 0.08674
    print(f"[!] 网络获取失败，使用缓存汇率: 100 卢布 = 8.67 人民币")
    return cached_rate


YANDEX_LOGISTICS_TABLE = [
    {
        "产品类型": "Extra Small",
        "配送方式": "GTA-SUPER ECONOMY Extra Small",
        "运输方式": "陆运",
        "资费公式": "178卢布/千克+99卢布/票",
        "重量区间": (0.001, 0.5),
        "货值区间": (1, 1500),
        "尺寸限制": {"type": "sum_and_max", "三边和": 90, "单边最长": 60},
        "电池运输": "可以运输内部装有电池的物品，无需提供材料安全性数据表MSDS"
    },
    {
        "产品类型": "标准",
        "配送方式": "GTA-SUPER ECONOMY",
        "运输方式": "陆运",
        "资费公式": "415卢布/千克+196卢布/票",
        "重量区间": (0.001, 30.0),
        "货值区间": (1501, 500000),
        "尺寸限制": {"type": "single_max", "单边最大": 150, "other_dims": (80, 80)},
        "电池运输": "可以运输内部装有电池的物品，无需提供材料安全性数据表MSDS"
    }
]


def parse_fee_formula(formula):
    match = re.match(r"(\d+)卢布/千克\+(\d+)卢布/票", formula)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0


def check_dimensions(dimensions, limit_info):
    l, w, h = dimensions
    limit_type = limit_info["type"]

    if limit_type == "sum_and_max":
        sum_limit = limit_info["三边和"]
        max_side_limit = limit_info["单边最长"]
        return (l + w + h) <= sum_limit and max(l, w, h) <= max_side_limit

    elif limit_type == "single_max":
        L_limit = limit_info["单边最大"]
        W_limit, H_limit = limit_info["other_dims"]
        sides = sorted([l, w, h], reverse=True)
        return sides[0] <= L_limit and sides[1] <= W_limit and sides[2] <= H_limit

    return False


def check_battery(battery_type, limit_text):
    battery_type = battery_type.lower()
    limit_text = limit_text.lower()
    if "不接带电" in limit_text or "只接普货" in limit_text:
        return battery_type == "不接电"
    elif "可以运输内部装有电池的物品" in limit_text:
        return battery_type in ["不接电", "内部装有电池"]
    return True


def cny_to_rub(cny_amount, exchange_rate):
    return cny_amount / exchange_rate


def get_user_input():
    print("\n" + "=" * 60)
    print("=== Yandex 物流运费计算器 (ECONOMY 陆运) ===")
    print("说明：请输入商品进货价，程序会计算(进货价+运费)x2.7的最终销售价")
    print("提示：输入 'b' 可返回上一步重新输入")
    print("=" * 60)

    steps = [
        ("包裹重量 (kg, 如 0.5)", "weight"),
        ("包裹长度 (cm, 如 20)", "length"),
        ("包裹宽度 (cm, 如 15)", "width"),
        ("包裹高度 (cm, 如 10)", "height"),
        ("商品进货价 (人民币 CNY, 如 200)", "purchase_price"),
    ]
    
    values = {}
    current_step = 0
    
    while current_step < len(steps):
        prompt_text, field_name = steps[current_step]
        
        try:
            user_input = input(f"\n{current_step + 1}. 请输入{prompt_text}: ").strip()
            
            if user_input.lower() == 'b':
                if current_step > 0:
                    current_step -= 1
                    print(f"  -> 返回上一步，重新输入: {steps[current_step][0]}")
                    continue
                else:
                    print("  -> 已经是第一步，无法返回")
                    continue
            
            values[field_name] = float(user_input)
            current_step += 1
            
        except ValueError:
            print("  [!] 输入错误：请输入有效的数字，或输入 'b' 返回上一步")
            continue
        except KeyboardInterrupt:
            print("\n\n用户取消输入。")
            return None
    
    print("\n6. 请选择电池类型：")
    print("   [1] 不接电 (普货，无电池)")
    print("   [2] 内部装有电池 (如蓝牙耳机、智能手表)")
    print("   [3] 纯电池 (如充电宝、单独电池)")
    
    while True:
        try:
            battery_choice = input("   请输入选项数字 (1/2/3): ").strip()
            
            if battery_choice.lower() == 'b':
                print("  -> 返回重新输入进货价...")
                return get_user_input()
            
            battery_map = {"1": "不接电", "2": "内部装有电池", "3": "纯电池"}
            if battery_choice in battery_map:
                battery_type = battery_map[battery_choice]
                break
            else:
                print("  [!] 请输入 1、2 或 3")
        except KeyboardInterrupt:
            print("\n\n用户取消输入。")
            return None

    return values["weight"], (values["length"], values["width"], values["height"]), values["purchase_price"], battery_type


def calculate_final_price(weight, dimensions, purchase_price, battery_type, exchange_rate):
    PRICE_MULTIPLIER = 2.7
    COMMISSION_RATE = 0.40
    
    value_rub = cny_to_rub(purchase_price, exchange_rate)

    print(f"\n商品进货价换算: {purchase_price:.2f} CNY = {value_rub:.2f} RUB")
    print(f"定价倍数: x{PRICE_MULTIPLIER}")
    print(f"佣金比例: {int(COMMISSION_RATE * 100)}%")
    print("-" * 50)

    print(f"\n计算结果 (汇率: 1 RUB = {exchange_rate:.4f} CNY)")
    print("=" * 60)

    all_results = []

    for channel in YANDEX_LOGISTICS_TABLE:
        weight_min, weight_max = channel["重量区间"]
        weight_ok = weight_min <= weight <= weight_max

        value_min, value_max = channel["货值区间"]
        value_ok = value_min <= value_rub <= value_max

        dimensions_ok = check_dimensions(dimensions, channel["尺寸限制"])
        battery_ok = check_battery(battery_type, channel["电池运输"])

        per_kg, per_ticket = parse_fee_formula(channel["资费公式"])
        total_fee_rub = weight * per_kg + per_ticket
        total_fee_cny = total_fee_rub * exchange_rate
        
        final_price_cny = (purchase_price + total_fee_cny) * PRICE_MULTIPLIER
        final_price_rub = final_price_cny / exchange_rate
        
        commission_cny = final_price_cny * COMMISSION_RATE
        commission_rub = final_price_rub * COMMISSION_RATE
        
        total_cost_cny = purchase_price + total_fee_cny
        total_cost_rub = value_rub + total_fee_rub
        
        actual_revenue_cny = final_price_cny - commission_cny
        actual_revenue_rub = final_price_rub - commission_rub
        
        profit_cny = actual_revenue_cny - total_cost_cny
        profit_rub = profit_cny / exchange_rate
        profit_margin = (profit_cny / total_cost_cny) * 100 if total_cost_cny > 0 else 0

        is_fully_match = weight_ok and value_ok and dimensions_ok and battery_ok

        channel_data = {
            **channel,
            "进货价_CNY": purchase_price,
            "进货价_RUB": value_rub,
            "运费_CNY": total_fee_cny,
            "运费_RUB": total_fee_rub,
            "总成本_CNY": total_cost_cny,
            "总成本_RUB": total_cost_rub,
            "最终售价_CNY": final_price_cny,
            "最终售价_RUB": final_price_rub,
            "佣金_CNY": commission_cny,
            "佣金_RUB": commission_rub,
            "实际收入_CNY": actual_revenue_cny,
            "实际收入_RUB": actual_revenue_rub,
            "利润_CNY": profit_cny,
            "利润_RUB": profit_rub,
            "利润率": profit_margin,
            "重量符合": weight_ok,
            "货值符合": value_ok,
            "尺寸符合": dimensions_ok,
            "电池符合": battery_ok,
            "完全匹配": is_fully_match
        }

        all_results.append(channel_data)

    for i, chan in enumerate(all_results, 1):
        if chan['完全匹配']:
            print(f"\n[OK] {chan['配送方式']} ({chan['运输方式']}) - 完全符合")
        else:
            print(f"\n[参考] {chan['配送方式']} ({chan['运输方式']}) - 部分条件不符合")
        
        print(f"   资费公式: {chan['资费公式']}")
        print(f"   +-- 匹配状态 -------------")
        print(f"   | 重量: {'[OK]' if chan['重量符合'] else '[X]'} (要求: {chan['重量区间'][0]}-{chan['重量区间'][1]} kg, 当前: {weight} kg)")
        print(f"   | 尺寸: {'[OK]' if chan['尺寸符合'] else '[X]'}")
        print(f"   | 电池: {'[OK]' if chan['电池符合'] else '[X]'}")
        print(f"   | 货值: {'[OK]' if chan['货值符合'] else '[X]'} (要求: {chan['货值区间'][0]}-{chan['货值区间'][1]} RUB, 当前: {value_rub:.0f} RUB)")
        print(f"   +-------------------------")
        print(f"   +-- 成本明细 -------------")
        print(f"   | 进货价:  {chan['进货价_CNY']:.2f} CNY  =  {chan['进货价_RUB']:.0f} RUB")
        print(f"   | 运费:    {chan['运费_CNY']:.2f} CNY  =  {chan['运费_RUB']:.0f} RUB")
        print(f"   | 总成本:  {chan['总成本_CNY']:.2f} CNY  =  {chan['总成本_RUB']:.0f} RUB")
        print(f"   +-------------------------")
        print(f"   +-- 最终定价 (x{PRICE_MULTIPLIER}倍) --")
        print(f"   | 最终售价: {chan['最终售价_CNY']:.2f} CNY")
        print(f"   | 最终售价: {chan['最终售价_RUB']:.0f} RUB")
        print(f"   +-------------------------")
        print(f"   +-- 佣金扣除 ({int(COMMISSION_RATE * 100)}%) --------")
        print(f"   | 平台佣金: {chan['佣金_CNY']:.2f} CNY  =  {chan['佣金_RUB']:.0f} RUB")
        print(f"   | 实际收入: {chan['实际收入_CNY']:.2f} CNY  =  {chan['实际收入_RUB']:.0f} RUB")
        print(f"   +-------------------------")
        print(f"   +-- 利润分析 -------------")
        print(f"   | 净利润:   {chan['利润_CNY']:.2f} CNY  =  {chan['利润_RUB']:.0f} RUB")
        print(f"   | 利润率:   {chan['利润率']:.1f}%")
        print(f"   +-------------------------")
        print(f"   电池限制: {chan['电池运输'][:50]}...")
        print("-" * 60)


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    print("=" * 60)
    print("Yandex 物流最终定价计算器 (ECONOMY 陆运)")
    print("=" * 60)
    print("说明：")
    print("1. 输入商品进货价，自动计算最终销售价格")
    print(f"2. 定价公式: 最终售价 = (进货价 + 运费) x 2.7")
    print("3. 汇率从网络获取，失败则使用缓存汇率")
    print("4. 结果显示人民币(CNY)和卢布(RUB)双货币")
    print("=" * 60)

    print("\n正在获取实时汇率...")
    exchange_rate = get_rub_to_cny_rate()
    print(f"当前汇率: 1 卢布 = {exchange_rate:.4f} 人民币")
    print(f"换算比例: 1 人民币 = {1 / exchange_rate:.2f} 卢布")

    while True:
        print("\n" + "=" * 60)
        print("新的定价计算")
        print("=" * 60)

        user_input = get_user_input()
        if not user_input:
            retry = input("\n是否重新输入？(Y/n): ").strip().lower()
            if retry in ['n', 'no', '否']:
                break
            continue

        weight, dimensions, purchase_price, battery_type = user_input
        calculate_final_price(weight, dimensions, purchase_price, battery_type, exchange_rate)

        print("\n" + "=" * 60)
        continue_choice = input("\n是否继续计算其他商品？(Y/n): ").strip().lower()

        if continue_choice in ['n', 'no', '否', '退出']:
            print("\n感谢使用 Yandex 物流定价计算器！")
            print("程序将在 3 秒后退出...")
            import time
            time.sleep(3)
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断。")
    except Exception as e:
        print(f"\n程序发生错误: {e}")
    finally:
        input("\n按 Enter 键退出程序...")
