from dateutil.parser import parse


# Filters


def contains(data, gear_filter):
    print(1)
    print(data)
    valid_data = []
    excluded_data = []
    for item in data:
        print(2)
        if gear_filter.comparison_data in item[gear_filter.field_name]:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def does_not_contain(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if gear_filter.comparison_data not in item[gear_filter.field_name]:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def equals(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if item[gear_filter.field_name] == gear_filter.comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def does_not_equal(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if item[gear_filter.field_name] != gear_filter.comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def is_empty(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if item[gear_filter.field_name] == "":  # TODO: REVISAR: gear_filter.comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def is_not_empty(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if item[gear_filter.field_name] != "":  # TODO: REVISAR: gear_filter.comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def starts_with(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if item[gear_filter.field_name].startswith(gear_filter.comparison_data):
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def does_not_start_with(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if not item[gear_filter.field_name].startswith(gear_filter.comparison_data):
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def ends_with(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if item[gear_filter.field_name].endswith(gear_filter.comparison_data):
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def does_not_end_with(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        if not item[gear_filter.field_name].endswith(gear_filter.comparison_data):
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def less_than(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        try:
            item_value = int(item[gear_filter.field_name])
            comparison_data = int(gear_filter.comparison_data)
        except Exception as e:
            try:
                item_value = parse(item[gear_filter.field_name])
                comparison_data = parse(gear_filter.comparison_data)
            except Exception as e:
                item_value = None
                comparison_data = None
        if (item_value is not None and comparison_data is not None) and \
                item_value < comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def greater_than(data, gear_filter):
    valid_data = []
    excluded_data = []
    for item in data:
        try:
            item_value = int(item[gear_filter.field_name])
            comparison_data = int(gear_filter.comparison_data)
        except Exception as e:
            try:
                item_value = parse(item[gear_filter.field_name])
                comparison_data = parse(gear_filter.comparison_data)
            except Exception as e:
                item_value = None
                comparison_data = None
        if (item_value is not None and comparison_data is not None) and \
                item_value > comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def length_equals(data, gear_filter):
    valid_data = []
    excluded_data = []
    try:
        comparison_data = int(gear_filter.comparison_data)
    except Exception as e:
        comparison_data = None
    for item in data:
        if comparison_data is not None and len(item[gear_filter.field_name]) == comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def length_is_less_than(data, gear_filter):
    valid_data = []
    excluded_data = []
    try:
        comparison_data = int(gear_filter.comparison_data)
    except Exception as e:
        comparison_data = None
    for item in data:
        if comparison_data is not None and len(item[gear_filter.field_name]) < comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data


def length_is_greater_than(data, gear_filter):
    valid_data = []
    excluded_data = []
    try:
        comparison_data = int(gear_filter.comparison_data)
    except Exception as e:
        comparison_data = None
    for item in data:
        if comparison_data is not None and len(item[gear_filter.field_name]) > comparison_data:
            valid_data.append(item)
        else:
            excluded_data.append(item)
    return valid_data, excluded_data