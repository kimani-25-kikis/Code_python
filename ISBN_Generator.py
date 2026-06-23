def calculate_check_digit_10(isbn):
    total = 0

    for i in range(9):
        total += int(isbn[i]) * (10 - i)

    remainder = total % 11
    check_digit = (11 - remainder) % 11

    if check_digit == 10:
        return 'X'

    return str(check_digit)


def calculate_check_digit_13(isbn):
    total = 0

    for i in range(12):
        if i % 2 == 0:
            total += int(isbn[i])
        else:
            total += int(isbn[i]) * 3

    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def validate_isbn(isbn, length):
    try:
        if length == 10:

            if len(isbn) != 10:
                print('ISBN-10 code should be 10 digits long.')
                return

            for char in isbn[:-1]:
                if not char.isdigit():
                    raise ValueError

            if not (isbn[-1].isdigit() or isbn[-1] == 'X'):
                raise ValueError

            if calculate_check_digit_10(isbn[:9]) == isbn[-1]:
                print('Valid ISBN Code.')
            else:
                print('Invalid ISBN Code.')

        elif length == 13:

            if len(isbn) != 13:
                print('ISBN-13 code should be 13 digits long.')
                return

            if not isbn.isdigit():
                raise ValueError

            if calculate_check_digit_13(isbn[:12]) == isbn[-1]:
                print('Valid ISBN Code.')
            else:
                print('Invalid ISBN Code.')

        else:
            print('Length should be 10 or 13.')

    except ValueError:
        print('Invalid character was found.')


def main():
    user_input = input('Enter ISBN and length: ')

    try:
        values = user_input.split(',')
        isbn = values[0]
        length = int(values[1])

    except IndexError:
        print('Enter comma-separated values.')
        return

    except ValueError:
        print('Length must be a number.')
        return

    validate_isbn(isbn, length)


# main()