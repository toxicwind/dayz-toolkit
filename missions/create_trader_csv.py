import re
import csv

def parse_price(price_str):
    if not price_str:
        return ""
    clean_price = price_str.lower().replace('$', '').replace(' ', '')
    multiplier = 1
    if 'k' in clean_price:
        multiplier = 1000
        clean_price = clean_price.replace('k', '')
    try:
        return int(float(clean_price) * multiplier)
    except ValueError:
        return price_str

def parse_line(line, category):
    # Pattern to match: •Item Name (Request info) (Sells: $Price / Buys: $Price)
    # or variants like (Sells: $Price)
    
    # Remove bullet point
    line = line.strip().lstrip('•').strip()
    
    # Extract item name and request info
    # Everything before the first '(' that starts "Sells" or "Buys" or "Request"
    
    # Better approach: Split by '('
    parts = line.split('(')
    item_name = parts[0].strip()
    
    sell_price = ""
    buy_price = ""
    notes = ""
    
    for part in parts[1:]:
        part = part.replace(')', '').strip()
        lower_part = part.lower()
        
        if 'sells:' in lower_part:
            # Handle split sells/buys in one parenthesis if formatted like "Sells: $25K/ Buys: $10K"
            if '/' in part and 'buys:' in lower_part:
                subparts = part.split('/')
                for sp in subparts:
                    if 'sells:' in sp.lower():
                        sell_price = parse_price(sp.split(':')[1].strip())
                    elif 'buys:' in sp.lower():
                        buy_price = parse_price(sp.split(':')[1].strip())
            else:
                sell_price = parse_price(part.split(':')[1].strip())
        
        elif 'buys:' in lower_part:
            buy_price = parse_price(part.split(':')[1].strip())
            
        elif 'request' in lower_part:
            notes = part
    
    return [category, item_name, sell_price, buy_price, notes]

def main():
    from vector.config import get_settings
    settings = get_settings()
    input_file = settings.chronos_root / 'trader_list.txt'
    output_file = settings.chronos_root / 'trader_items.csv'
    
    category = "Uncategorized"
    data = []
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if not line.startswith('•'):
            category = line
            continue
            
        data.append(parse_line(line, category))
        
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Item Name', 'Sell Price', 'Buy Price', 'Notes'])
        writer.writerows(data)
        
    print(f"CSV created at {output_file}")

if __name__ == "__main__":
    main()
