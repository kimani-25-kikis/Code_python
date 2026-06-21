import re

car_records = [
    {
        'car_id': 'C1001',
        'make': 'Toyota',
        'model': 'Corolla',
        'year': 2020,
        'owner': 'John Doe',
        'service_codes': ['S101', 'S205'],
    },
    {
        'car_id': 'c1002',
        'make': 'Honda',
        'model': 'Civic',
        'year': 2018,
        'owner': 'Jane Smith',
        'service_codes': ['S102', 'S310'],
    },
    {
        'car_id': 'C1003',
        'make': 'Ford',
        'model': 'Focus',
        'year': 2022,
        'owner': 'Michael Brown',
        'service_codes': ['S150'],
    }
]


def find_invalid_records(
    car_id, make, model, year, owner, service_codes
):
    constraints = {
        'car_id': isinstance(car_id, str)
        and re.fullmatch(r'c\d+', car_id, re.IGNORECASE),

        'make': isinstance(make, str) and len(make) > 0,

        'model': isinstance(model, str) and len(model) > 0,

        'year': isinstance(year, int) and 1900 <= year <= 2030,

        'owner': isinstance(owner, str) and len(owner) > 0,

        'service_codes': isinstance(service_codes, list)
        and all(
            re.fullmatch(r's\d+', code, re.IGNORECASE)
            for code in service_codes
        )
    }

    return [key for key, value in constraints.items() if not value]


def validate(data):
    if not isinstance(data, (list, tuple)):
        print('Invalid format: expected a list or tuple.')
        return False

    is_invalid = False

    key_set = {
        'car_id',
        'make',
        'model',
        'year',
        'owner',
        'service_codes'
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
                f'Invalid format: {dictionary} at position {index} has missing and/or invalid keys.'
            )
            is_invalid = True
            continue

        invalid_records = find_invalid_records(**dictionary)

        for key in invalid_records:
            print(
                f"Unexpected format '{key}: {dictionary[key]}' at position {index}."
            )
            is_invalid = True

    if is_invalid:
        return False

    print('Valid format.')
    return True


validate(car_records)