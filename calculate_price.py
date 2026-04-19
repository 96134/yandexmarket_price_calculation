import re
import requests
import os
from datetime import datetime


# ---------- 汇率获取模块 ----------
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
                        print(f"✅ 汇率已更新: 100 卢布 ≈ {rate_per_100rub:.2f} 人民币 (数据源: 新浪外汇)")
                        return rate_per_100rub / 100.0
        except Exception:
            pass
        return None
    
    def try_cmb():
        try:
            url = "https://fx.cmbchina.com/api/v1/fxrate/getfxrate"
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            if data.get('success'):
                for item in data.get('data', []):
                    if item.get('ccyNbrEn') == 'RUB':
                        rate = float(item.get('rtbBid', 0)) / 100
                        if rate > 0:
                            print(f"✅ 汇率已更新: 100 卢布 ≈ {rate*100:.2f} 人民币 (数据源: 招商银行)")
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
                print(f"✅ 汇率已更新: 100 卢布 ≈ {rate*100:.2f} 人民币 (数据源: ExchangeRate-API)")
                return rate
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
                print(f"✅ 汇率已更新: 100 卢布 ≈ {rate*100:.2f} 人民币 (数据源: Frankfurter)")
                return rate
        except Exception:
            pass
        return None
    
    for source_func in [try_sina, try_frankfurter, try_exchange_rate_api, try_cmb]:
        result = source_func()
        if result:
            return result
    
    cached_rate = 0.08674
    print(f"⚠️  网络获取失败，使用缓存汇率: 100 卢布 ≈ 8.67 人民币")
    return cached_rate


# ---------- 内置物流数据 ----------
YANDEX_LOGISTICS_TABLE = [
    {
        "产品类型": "Extra Small",
        "配送方式": "GTA-SUPER EXPRESS Extra Small",
        "运输方式": "空运",
        "资费公式": "525卢布/千克+99卢布/票",
        "重量区间": (0.001, 0.5),
        "货值区间": (1, 1500),  # 卢布
        "尺寸限制": {"type": "sum_and_max", "三边和": 90, "单边最长": 60},
        "电池运输": "电池不允许，只接普货（不接带电、带磁、液体、粉末、刀具、仿牌等产品）"
    },
    {
        "产品类型": "Extra Small",
        "配送方式": "GTA-EXPRESS Extra Small",
        "运输方式": "陆空联运",
        "资费公式": "428卢布/千克+81卢布/票",
        "重量区间": (0.001, 0.5),
        "货值区间": (1, 1500),  # 卢布
        "尺寸限制": {"type": "sum_and_max", "三边和": 90, "单边最长": 60},
        "电池运输": "可以运输内部装有电池的物品，无需提供材料安全性数据表MSDS，最大功率为160瓦特一小时"
    },
    {
        "产品类型": "Extra Small",
        "配送方式": "GTA-SUPER ECONOMY Extra Small",
        "运输方式": "陆运",
        "资费公式": "178卢布/千克+99卢布/票",
        "重量区间": (0.001, 0.5),
        "货值区间": (1, 1500),  # 卢布
        "尺寸限制": {"type": "sum_and_max", "三边和": 90, "单边最长": 60},
        "电池运输": "可以运输内部装有电池的物品，无需提供材料安全性数据表MSDS"
    },
    {
        "产品类型": "标准",
        "配送方式": "GTA-SUPER EXPRESS",
        "运输方式": "空运",
        "资费公式": "1058卢布/千克+196卢布/票",
        "重量区间": (0.001, 30.0),
        "货值区间": (1501, 500000),  # 卢布
        "尺寸限制": {"type": "single_max", "单边最大": 150, "other_dims": (80, 80)},
        "电池运输": "电池不允许，只接普货（不接带电、带磁、液体、粉末、刀具、仿牌等产品）"
    },
    {
        "产品类型": "标准",
        "配送方式": "GTA-EXPRESS",
        "运输方式": "陆空联运",
        "资费公式": "697卢布/千克+183卢布/票",
        "重量区间": (0.001, 30.0),
        "货值区间": (1501, 500000),  # 卢布
        "尺寸限制": {"type": "single_max", "单边最大": 150, "other_dims": (80, 80)},
        "电池运输": "可以运输内部装有电池的物品，无需提供材料安全性数据表MSDS，最大功率为160瓦特一小时"
    },
    {
        "产品类型": "标准",
        "配送方式": "GTA-SUPER ECONOMY",
        "运输方式": "陆运",
        "资费公式": "415卢布/千克+196卢布/票",
        "重量区间": (0.001, 30.0),
        "货值区间": (1501, 500000),  # 卢布
        "尺寸限制": {"type": "single_max", "单边最大": 150, "other_dims": (80, 80)},
        "电池运输": "可以运输内部装有电池的物品，无需提供材料安全性数据表MSDS"
    }
]


# ---------- 核心计算函数 ----------
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

        # 获取三条边并排序（从大到小）
        sides = sorted([l, w, h], reverse=True)

        # 检查最长边 ≤ L_limit，且其他两边分别 ≤ W_limit 和 H_limit
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
    """人民币换算为卢布"""
    return cny_amount / exchange_rate


def get_user_input():
    print("\n" + "=" * 60)
    print("=== Yandex 物流运费计算器（最终定价版）===")
    print("说明：请输入商品进货价，程序会计算(进货价+运费)×2.63的最终销售价")
    print("=" * 60)

    try:
        weight = float(input("\n1. 请输入包裹重量 (kg, 如 0.5): "))
        length = float(input("2. 请输入包裹长度 (cm, 如 20): "))
        width = float(input("3. 请输入包裹宽度 (cm, 如 15): "))
        height = float(input("4. 请输入包裹高度 (cm, 如 10): "))
        purchase_price = float(input("5. 请输入商品进货价 (人民币 CNY, 如 200): "))

        print("\n6. 请选择电池类型：")
        print("   [1] 不接电 (普货，无电池)")
        print("   [2] 内部装有电池 (如蓝牙耳机、智能手表)")
        print("   [3] 纯电池 (如充电宝、单独电池)")
        battery_choice = input("   请输入选项数字 (1/2/3): ")

        battery_map = {"1": "不接电", "2": "内部装有电池", "3": "纯电池"}
        battery_type = battery_map.get(battery_choice, "不接电")

        return weight, (length, width, height), purchase_price, battery_type
    except ValueError:
        print("输入错误：请确保输入的是有效的数字。")
        return None
    except KeyboardInterrupt:
        print("\n\n用户取消输入。")
        return None


def calculate_final_price(weight, dimensions, purchase_price, battery_type, exchange_rate):
    """执行最终定价计算逻辑：最终售价 = (进货价 + 运费) × 2.63"""
    # 定价倍数
    PRICE_MULTIPLIER = 2.63
    
    # 人民币换算为卢布
    value_rub = cny_to_rub(purchase_price, exchange_rate)

    print(f"\n商品进货价换算: {purchase_price:.2f} CNY ≈ {value_rub:.2f} RUB")
    print(f"定价倍数: ×{PRICE_MULTIPLIER}")
    print("-" * 50)

    print(f"\n匹配结果 (汇率: 1 RUB ≈ {exchange_rate:.4f} CNY)")
    print("=" * 60)

    # 分为两种结果：完全匹配和部分匹配（仅货值不符合）
    fully_matched_channels = []
    partially_matched_channels = []
    not_match_reasons = []

    for channel in YANDEX_LOGISTICS_TABLE:
        # 检查重量
        weight_min, weight_max = channel["重量区间"]
        weight_ok = weight_min <= weight <= weight_max

        # 检查货值
        value_min, value_max = channel["货值区间"]
        value_ok = value_min <= value_rub <= value_max

        # 检查尺寸
        dimensions_ok = check_dimensions(dimensions, channel["尺寸限制"])

        # 检查电池
        battery_ok = check_battery(battery_type, channel["电池运输"])

        # 计算运费（无论是否匹配都计算）
        per_kg, per_ticket = parse_fee_formula(channel["资费公式"])
        total_fee_rub = weight * per_kg + per_ticket
        total_fee_cny = total_fee_rub * exchange_rate  # 运费换算为人民币
        
        # 计算最终售价：(进货价 + 运费) × 2.63
        final_price_cny = (purchase_price + total_fee_cny) * PRICE_MULTIPLIER
        final_price_rub = final_price_cny / exchange_rate  # 换算为卢布
        
        # 计算成本总和
        total_cost_cny = purchase_price + total_fee_cny
        total_cost_rub = value_rub + total_fee_rub
        
        # 计算利润率
        profit_cny = final_price_cny - total_cost_cny
        profit_rub = profit_cny / exchange_rate
        profit_margin = (profit_cny / total_cost_cny) * 100 if total_cost_cny > 0 else 0

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
            "利润_CNY": profit_cny,
            "利润_RUB": profit_rub,
            "利润率": profit_margin,
            "重量符合": weight_ok,
            "货值符合": value_ok,
            "尺寸符合": dimensions_ok,
            "电池符合": battery_ok
        }

        # 如果所有条件都满足
        if weight_ok and value_ok and dimensions_ok and battery_ok:
            fully_matched_channels.append(channel_data)
        elif weight_ok and dimensions_ok and battery_ok:
            # 仅货值不符合，但仍计算运费
            partially_matched_channels.append(channel_data)
        else:
            # 记录不匹配的原因
            reasons = []
            if not weight_ok:
                reasons.append(f"重量 {weight}kg 不在 {weight_min}-{weight_max}kg 范围内")
            if not value_ok:
                reasons.append(f"货值 {value_rub:.2f} RUB 不在 {value_min}-{value_max} RUB 范围内")
            if not dimensions_ok:
                limit_type = channel["尺寸限制"]["type"]
                if limit_type == "sum_and_max":
                    reasons.append(
                        f"尺寸不符合: 三边和 ≤ {channel['尺寸限制']['三边和']}cm, 单边最长 ≤ {channel['尺寸限制']['单边最长']}cm")
                elif limit_type == "single_max":
                    L_limit = channel["尺寸限制"]["单边最大"]
                    W_limit, H_limit = channel["尺寸限制"]["other_dims"]
                    reasons.append(f"尺寸不符合: 最长边 ≤ {L_limit}cm, 其他两边 ≤ {W_limit}cm 和 {H_limit}cm")
            if not battery_ok:
                reasons.append(f"电池类型 '{battery_type}' 不符合: {channel['电池运输'][:30]}...")

            not_match_reasons.append({
                "渠道": channel["配送方式"],
                "原因": reasons
            })

    # 显示完全匹配的结果
    if fully_matched_channels:
        print(f"\n✅ 找到 {len(fully_matched_channels)} 个完全符合条件的渠道：\n")
        for i, chan in enumerate(fully_matched_channels, 1):
            print(f"[选项 {i}] {chan['配送方式']} ({chan['运输方式']})")
            print(f"   资费公式: {chan['资费公式']}")
            
            # 显示成本构成（CNY + RUB）
            print(f"   ┌─ 成本明细 ──────────────")
            print(f"   │ 进货价:  {chan['进货价_CNY']:.2f} CNY  ≈  {chan['进货价_RUB']:.0f} RUB")
            print(f"   │ 运费:    {chan['运费_CNY']:.2f} CNY  ≈  {chan['运费_RUB']:.0f} RUB")
            print(f"   │ 总成本:  {chan['总成本_CNY']:.2f} CNY  ≈  {chan['总成本_RUB']:.0f} RUB")
            print(f"   └───────────────────────")
            
            # 显示最终定价（CNY + RUB）
            print(f"   ┌─ 最终定价 (×{PRICE_MULTIPLIER}倍) ─")
            print(f"   │ 最终售价: {chan['最终售价_CNY']:.2f} CNY")
            print(f"   │ 最终售价: {chan['最终售价_RUB']:.0f} RUB")
            print(f"   └───────────────────────")
            
            # 显示利润分析（CNY + RUB）
            print(f"   ┌─ 利润分析 ─────────────")
            print(f"   │ 利润:     {chan['利润_CNY']:.2f} CNY  ≈  {chan['利润_RUB']:.0f} RUB")
            print(f"   │ 利润率:   {chan['利润率']:.1f}%")
            print(f"   └───────────────────────")
            
            # 电池限制
            print(f"   电池限制: {chan['电池运输'][:50]}...")
            print("-" * 60)

        # 推荐最优选项（基于利润率最高）
        if fully_matched_channels:
            # 按利润率排序
            sorted_by_margin = sorted(fully_matched_channels, key=lambda x: x['利润率'], reverse=True)
            best_by_margin = sorted_by_margin[0]
            
            # 按最终售价最低排序
            sorted_by_price = sorted(fully_matched_channels, key=lambda x: x['最终售价_CNY'])
            best_by_price = sorted_by_price[0]
            
            print(f"\n💡 最优推荐 (利润率最高): {best_by_margin['配送方式']}")
            print(f"   最终售价: {best_by_margin['最终售价_CNY']:.2f} CNY  ≈  {best_by_margin['最终售价_RUB']:.0f} RUB")
            print(f"   利润率:   {best_by_margin['利润率']:.1f}%")
            
            print(f"\n💡 价格最优 (售价最低): {best_by_price['配送方式']}")
            print(f"   最终售价: {best_by_price['最终售价_CNY']:.2f} CNY  ≈  {best_by_price['最终售价_RUB']:.0f} RUB")
            print(f"   利润率:   {best_by_price['利润率']:.1f}%")
    
    # 显示部分匹配的结果（仅货值不符合）
    if partially_matched_channels and not fully_matched_channels:
        print(f"\n⚠️  注意：货值 {value_rub:.2f} RUB 不符合任何渠道的货值要求")
        print(f"    但以下渠道在重量、尺寸、电池方面符合要求，可参考运费：\n")
        
        for i, chan in enumerate(partially_matched_channels, 1):
            print(f"[参考 {i}] {chan['配送方式']} ({chan['运输方式']})")
            print(f"   资费公式: {chan['资费公式']}")
            
            # 显示匹配状态
            print(f"   ┌─ 匹配状态 ──────────────")
            print(f"   │ 重量: {'✅' if chan['重量符合'] else '❌'}")
            print(f"   │ 尺寸: {'✅' if chan['尺寸符合'] else '❌'}")
            print(f"   │ 电池: {'✅' if chan['电池符合'] else '❌'}")
            print(f"   │ 货值: ❌ (要求: {chan['货值区间'][0]}-{chan['货值区间'][1]} RUB)")
            print(f"   │       当前: {value_rub:.2f} RUB")
            print(f"   └───────────────────────")
            
            # 显示成本构成（CNY + RUB）
            print(f"   ┌─ 成本明细 ──────────────")
            print(f"   │ 进货价:  {chan['进货价_CNY']:.2f} CNY  ≈  {chan['进货价_RUB']:.0f} RUB")
            print(f"   │ 运费:    {chan['运费_CNY']:.2f} CNY  ≈  {chan['运费_RUB']:.0f} RUB")
            print(f"   │ 总成本:  {chan['总成本_CNY']:.2f} CNY  ≈  {chan['总成本_RUB']:.0f} RUB")
            print(f"   └───────────────────────")
            
            # 显示最终定价（CNY + RUB）
            print(f"   ┌─ 最终定价 (×{PRICE_MULTIPLIER}倍) ─")
            print(f"   │ 最终售价: {chan['最终售价_CNY']:.2f} CNY")
            print(f"   │ 最终售价: {chan['最终售价_RUB']:.0f} RUB")
            print(f"   └───────────────────────")
            
            # 电池限制
            print(f"   电池限制: {chan['电池运输'][:50]}...")
            print("-" * 60)
        
        # 给出货值调整建议
        print(f"\n💡 货值调整建议：")
        if value_rub < 1:
            print(f"  - 当前货值 ({value_rub:.2f} RUB) 过低，需要 ≥ 1 RUB")
        elif value_rub > 500000:
            print(f"  - 当前货值 ({value_rub:.2f} RUB) 过高，需要 ≤ 500,000 RUB")
        elif 1500 < value_rub < 1501:
            print(f"  - 当前货值在间隙中，建议调整为 ≤ 1500 RUB 或 ≥ 1501 RUB")
        
        # 显示运费最低的参考渠道
        if partially_matched_channels:
            cheapest = min(partially_matched_channels, key=lambda x: x['运费_CNY'])
            print(f"\n📦 参考运费最低: {cheapest['配送方式']}")
            print(f"   运费: {cheapest['运费_CNY']:.2f} CNY  ≈  {cheapest['运费_RUB']:.0f} RUB")
    
    # 完全没有匹配结果
    if not fully_matched_channels and not partially_matched_channels:
        print(f"\n⚠️  未找到符合条件的物流渠道。")
        print(f"详细分析：")

        # 提供详细的原因分析
        value_rub_rounded = round(value_rub, 2)
        max_dim = max(dimensions)
        sum_dim = sum(dimensions)

        # 货值分析
        if value_rub_rounded < 1:
            print(f"  ❌ 货值过低 ({value_rub_rounded} RUB < 1 RUB)")
        elif value_rub_rounded > 500000:
            print(f"  ❌ 货值过高 ({value_rub_rounded} RUB > 500,000 RUB)")
        elif 1500 < value_rub_rounded < 1501:
            print(f"  ⚠️  货值 {value_rub_rounded} RUB 在 Extra Small (≤1500 RUB) 和 标准 (≥1501 RUB) 渠道之间")

        # 尺寸分析
        if max_dim > 150:
            print(f"  ❌ 最长边 {max_dim} cm 超出所有渠道限制 (最大 150 cm)")

        # Extra Small 渠道的特别限制
        if max_dim > 60:
            print(f"  ❌ Extra Small 渠道限制：最长边 ≤ 60 cm (您的包裹最长边为 {max_dim} cm)")

        if sum_dim > 90:
            print(f"  ❌ Extra Small 渠道限制：三边和 ≤ 90 cm (您的包裹三边和为 {sum_dim} cm)")

        # 列出各个渠道的具体原因
        print(f"\n各渠道详细不匹配原因：")
        for reason_info in not_match_reasons:
            print(f"\n  {reason_info['渠道']}:")
            for reason in reason_info['原因']:
                print(f"    - {reason}")

        # 给出建议
        print(f"\n💡 建议调整方案：")
        if value_rub_rounded < 1501 and max_dim <= 60 and sum_dim <= 90 and weight <= 0.5:
            print(f"  - 您的包裹符合 Extra Small 渠道的尺寸和重量要求")
            print(f"  - 但货值 {value_rub_rounded:.2f} RUB 需要 ≤ 1500 RUB 或 ≥ 1501 RUB")
            print(f"  - 建议调整货值到 ≤ 1500 RUB 或 ≥ 1501 RUB")
        elif value_rub_rounded >= 1501 and weight <= 30:
            print(f"  - 您的包裹符合标准渠道的货值和重量要求")
            print(f"  - 但尺寸可能需要调整，请检查最长边 ≤ 150cm，其他两边 ≤ 80cm")


def main():
    # 清屏
    os.system('cls' if os.name == 'nt' else 'clear')

    # 显示欢迎信息
    print("=" * 60)
    print("Yandex 物流最终定价计算器")
    print("=" * 60)
    print("说明：")
    print("1. 输入商品进货价，自动计算最终销售价格")
    print(f"2. 定价公式: 最终售价 = (进货价 + 运费) × 2.63")
    print("3. 汇率从网络获取，失败则使用缓存汇率")
    print("4. 结果显示人民币(CNY)和卢布(RUB)双货币")
    print("5. 即使货值不符合，也会显示参考运费")
    print("=" * 60)

    # 启动时获取汇率
    print("\n正在获取实时汇率...")
    exchange_rate = get_rub_to_cny_rate()  # 1 RUB = X CNY
    print(f"当前汇率: 1 卢布 ≈ {exchange_rate:.4f} 人民币")
    print(f"换算比例: 1 人民币 ≈ {1 / exchange_rate:.2f} 卢布")

    # 主循环
    while True:
        print("\n" + "=" * 60)
        print("新的定价计算")
        print("=" * 60)

        user_input = get_user_input()
        if not user_input:
            # 询问是否重试
            retry = input("\n是否重新输入？(y/n): ").strip().lower()
            if retry != 'y':
                break
            continue

        weight, dimensions, purchase_price, battery_type = user_input

        # 执行计算
        calculate_final_price(weight, dimensions, purchase_price, battery_type, exchange_rate)

        # 询问是否继续
        print("\n" + "=" * 60)
        continue_choice = input("\n是否继续计算其他商品？(y/n): ").strip().lower()

        if continue_choice not in ['y', 'yes', '是', '继续']:
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