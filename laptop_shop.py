import re

laptop_records = [
    {
        'laptop_id': 'L1001',
        'brand': 'Dell',
        'model': 'Inspiron 15',
        'price': 750.00,
        'quantity': 12,
        'processor': 'Intel Core i5',
        'serial_numbers': ['SN10001', 'SN10002']
    },
    {
        'laptop_id': 'L1002',
        'brand': 'HP',
        'model': 'Pavilion',
        'price': 650.50,
        'quantity': 8,
        'processor': 'AMD Ryzen 5',
        'serial_numbers': ['SN10003', 'SN10004']
    },
    {
        'laptop_id': 'L1003',
        'brand': 'Lenovo',
        'model': 'ThinkPad E14',
        'price': 899.99,
        'quantity': 5,
        'processor': 'Intel Core i7',
        'serial_numbers': ['SN10005']
    }
]


def find_invalid_records(
    laptop_id,
    brand,
    model,
    price,
    quantity,
    processor,
    serial_numbers
):
    constraints = {
        'laptop_id': isinstance(laptop_id, str)
        and re.fullmatch(r'l\d+', laptop_id, re.IGNORECASE),

        'brand': isinstance(brand, str) and len(brand) > 0,

        'model': isinstance(model, str) and len(model) > 0,

        'price': isinstance(price, (int, float)) and price > 0,

        'quantity': isinstance(quantity, int) and quantity >= 0,

        'processor': isinstance(processor, str) and len(processor) > 0,

        'serial_numbers': isinstance(serial_numbers, list)
        and all(
            re.fullmatch(r'SN\d+', serial, re.IGNORECASE)
            for serial in serial_numbers
        )
    }

    return [key for key, value in constraints.items() if not value]


def validate(data):
    if not isinstance(data, (list, tuple)):
        print('Invalid format: expected a list or tuple.')
        return False

    is_invalid = False

    key_set = {
        'laptop_id',
        'brand',
        'model',
        'price',
        'quantity',
        'processor',
        'serial_numbers'
    }

    for index, dictionary in enumerate(data):

        if not isinstance(dictionary, dict):
            print(
                f'Invalid format: expected a dictionary at position {index}.'
            )
            is_invalid = True
            continue

        if set(dictionary.keys()) != key_set:
            print(
                f'Invalid format: {dictionary} at position {index} '
                'has missing and/or invalid keys.'
            )
            is_invalid = True
            continue

        invalid_records = find_invalid_records(**dictionary)

        for key in invalid_records:
            print(
                f"Unexpected format '{key}: {dictionary[key]}' "
                f'at position {index}.'
            )
            is_invalid = True

    if is_invalid:
        return False

    print('Valid format.')
    return True


validate(laptop_records)