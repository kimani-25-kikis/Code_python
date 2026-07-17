def verify_card_number(card_number):
    # Remove spaces and dashes
    card_number = card_number.replace(" ", "").replace("-", "")

    total = 0
    reverse_digits = card_number[::-1]

    for i, digit in enumerate(reverse_digits):
        num = int(digit)

        # Double every second digit (excluding the check digit)
        if i % 2 == 1:
            num *= 2
            if num > 9:
                num -= 9

        total += num

    if total % 10 == 0:
        return "VALID!"
    else:
        return "INVALID!"